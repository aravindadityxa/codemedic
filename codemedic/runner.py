"""Runtime runner – executes Python code and captures detailed error information."""

from __future__ import annotations

import io
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

from .analyzer import AnalysisIssue, CodeAnalyzer
from .config import Config
from .explanations import ExplanationEngine
from .fixer import Fixer, PatchSuggestion
from .trace import TraceCollector, TraceResult

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Result of running a script with CodeMedic.

    Attributes:
        success: Whether the code ran without raising an exception.
        error: The raised exception, if any.
        trace: Structured trace data collected from the exception.
        explanation: Human-friendly explanation dictionary.
        fixes: List of patch suggestions.
        analysis: Static analysis issues found before execution.
        stdout: Captured standard output.
        stderr: Captured standard error.
    """

    success: bool
    error: Optional[BaseException] = None
    trace: Optional[TraceResult] = None
    explanation: Optional[dict[str, Any]] = None
    fixes: list[PatchSuggestion] = field(default_factory=list)
    analysis: list[AnalysisIssue] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary (safe for JSON)."""
        root = (
            self.explanation.get("root_cause", {})
            if self.explanation
            else {}
        )
        result = {
            "success": self.success,
            "error_type": self.trace.exception_type if self.trace else None,
            "message": self.trace.exception_message if self.trace else None,
            "what_happened": (
                self.explanation.get("what_happened", "")
                if self.explanation else ""
            ),
            "why_happened": (
                self.explanation.get("why_happened", "")
                if self.explanation else ""
            ),
            "simple_explanation": (
                self.explanation.get("simple_explanation", "")
                if self.explanation else ""
            ),
            "analogy": (
                self.explanation.get("analogy", "")
                if self.explanation else ""
            ),
            "common_causes": (
                self.explanation.get("common_causes", "")
                if self.explanation else ""
            ),
            "how_to_avoid": (
                self.explanation.get("how_to_avoid", "")
                if self.explanation else ""
            ),
            "root_cause": root,
            "fixes": [f.to_dict() for f in self.fixes],
            "analysis": [
                {
                    "line": i.line,
                    "column": i.column,
                    "message": i.message,
                    "severity": i.severity,
                    "category": i.category,
                }
                for i in self.analysis
            ],
            "full_traceback": self.trace.full_traceback if self.trace else "",
            "stdout": self.stdout,
            "stderr": self.stderr,
            "docs_reference": (
                self.explanation.get("docs_reference", "")
                if self.explanation else ""
            ),
        }
        return result


class Runner:
    """Executes Python code and captures detailed error context.

    .. warning::
        :meth:`run_file` and :meth:`run_code` use ``exec()`` to run arbitrary
        code. Only run code you trust. CodeMedic will warn about ``eval()``
        and ``exec()`` detected in the target source via the security checker.

    Args:
        mode: Explanation mode – ``"beginner"`` or ``"professional"``.
        config: Optional :class:`~codemedic.config.Config` object.
    """

    def __init__(
        self,
        mode: str = "beginner",
        config: Optional[Config] = None,
    ) -> None:
        self.config: Config = config or Config()
        self.mode: str = mode
        self._trace_collector = TraceCollector()
        self._explanation_engine = ExplanationEngine(mode=mode)
        self._fixer = Fixer()
        self._analyzer = CodeAnalyzer()

    def run_file(self, filepath: Union[str, Path]) -> RunResult:
        """Run a Python file and capture any exception.

        Raises:
            FileNotFoundError: If *filepath* does not exist.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        code = path.read_text(encoding="utf-8")
        return self.run_code(code, filename=str(path))

    def run_code(self, code: str, filename: str = "<string>") -> RunResult:
        """Run a source string and capture any exception.

        Static analysis runs first (non-blocking), then the code executes
        in an isolated namespace.
        """
        analysis = self._analyzer.analyze_code(code, filename=filename)

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        try:
            compiled = compile(code, filename, "exec")
        except SyntaxError as exc:
            trace = (
                self._trace_collector.collect_from_exception(
                    SyntaxError, exc, exc.__traceback__
                )
            )
            explanation = self._explanation_engine.explain(trace)
            fixes = self._fixer.suggest_fixes(trace)
            return RunResult(
                success=False,
                error=exc,
                trace=trace,
                explanation=explanation,
                fixes=fixes,
                analysis=analysis,
            )

        globals_dict: dict[str, Any] = {
            "__name__": "__main__",
            "__file__": filename,
            "__builtins__": __builtins__,
        }

        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compiled, globals_dict)  # noqa: S102 – intentional runner
            return RunResult(
                success=True,
                analysis=analysis,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
            )
        except Exception:  # noqa: BLE001
            exc_info = sys.exc_info()
            exc_type = exc_info[0]
            exc_value = exc_info[1]
            exc_tb = exc_info[2]
            if exc_type is not None and exc_value is not None:
                trace = (
                    self._trace_collector.collect_from_exception(
                        exc_type, exc_value, exc_tb
                    )
                )
            else:
                return RunResult(
                    success=False,
                    error=None,
                    trace=None,
                    analysis=analysis,
                    stdout=stdout_buf.getvalue(),
                    stderr=stderr_buf.getvalue(),
                )
            explanation = self._explanation_engine.explain(trace)
            fixes = self._fixer.suggest_fixes(trace)
            return RunResult(
                success=False,
                error=exc_value,
                trace=trace,
                explanation=explanation,
                fixes=fixes,
                analysis=analysis,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
            )

    def run_with_capture(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> RunResult:
        """Run a callable and capture any exception.

        Useful for integrating CodeMedic into existing applications without
        a source file.
        """
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                func(*args, **kwargs)
            return RunResult(
                success=True,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
            )
        except Exception:  # noqa: BLE001
            exc_info = sys.exc_info()
            exc_type = exc_info[0]
            exc_value = exc_info[1]
            exc_tb = exc_info[2]
            if exc_type is not None and exc_value is not None:
                trace = (
                    self._trace_collector.collect_from_exception(
                        exc_type, exc_value, exc_tb
                    )
                )
            else:
                return RunResult(
                    success=False,
                    error=None,
                    trace=None,
                    stdout=stdout_buf.getvalue(),
                    stderr=stderr_buf.getvalue(),
                )
            explanation = self._explanation_engine.explain(trace)
            fixes = self._fixer.suggest_fixes(trace)
            return RunResult(
                success=False,
                error=exc_value,
                trace=trace,
                explanation=explanation,
                fixes=fixes,
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
            )
