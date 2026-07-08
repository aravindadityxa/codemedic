"""Explanation engine – turns a raw exception into human-friendly output."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .database import KnowledgeBase
from .trace import TraceResult

logger = logging.getLogger(__name__)


class ExplanationEngine:
    """Generates structured explanations for Python exceptions.

    Supports two modes:

    * ``"beginner"`` – plain-English, analogies, simple fix hints.
    * ``"professional"`` – adds full traceback, docs URL, difficulty rating.

    Args:
        knowledge_base: :class:`~codemedic.database.KnowledgeBase` instance.
            If *None*, a default instance is created.
        mode: Explanation verbosity mode.
    """

    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        mode: str = "beginner",
    ) -> None:
        self.kb: KnowledgeBase = knowledge_base or KnowledgeBase()
        self.mode: str = mode

    def explain(self, trace: TraceResult) -> dict[str, Any]:
        """Generate a full explanation dictionary for *trace*.

        Returns a dict with keys: ``error_type``, ``message``,
        ``what_happened``, ``why_happened``, ``simple_explanation``,
        ``analogy``, ``common_causes``, ``how_to_avoid``, ``difficulty``,
        ``root_cause``, and optionally ``docs_reference``, ``full_traceback``,
        ``example_before``, ``example_after``, ``category``.
        """
        exc_type = trace.exception_type
        info = self.kb.get_error_info(exc_type)

        result: dict[str, Any] = {
            "error_type": exc_type,
            "message": trace.exception_message,
            "what_happened": self._what_happened(info, exc_type),
            "why_happened": self._why_happened(info, exc_type),
            "simple_explanation": self._simple_explanation(info, exc_type),
            "analogy": self._analogy(info, exc_type),
            "common_causes": self._common_causes(info),
            "how_to_avoid": self._how_to_avoid(info),
            "difficulty": self._difficulty(info),
            "category": info.get("category", "general") if info else "general",
            "root_cause": self._root_cause(trace),
        }

        if info:
            result["example_before"] = info.get("example_before", "")
            result["example_after"] = info.get("example_after", "")

        if self.mode == "professional":
            result["docs_reference"] = self._docs_reference(info, exc_type)
            result["full_traceback"] = trace.full_traceback
            result["chained_cause"] = (
                self.explain(trace.chained_cause) if trace.chained_cause else None
            )

        return result

    def explain_by_name(self, exception_name: str) -> dict[str, Any]:
        """Return an explanation for an exception class name without a live trace.

        Useful for ``codemedic explain TypeError`` from the CLI.
        """
        from .trace import TraceResult

        dummy_trace = TraceResult(
            exception_type=exception_name,
            exception_message=f"Example {exception_name}",
            exception_repr=f"{exception_name}()",
            frames=[],
            full_traceback="",
        )
        return self.explain(dummy_trace)

    def _what_happened(self, info: Optional[dict[str, Any]], exc_type: str) -> str:
        if info and info.get("description"):
            return str(info["description"])
        return f"A {exc_type} exception was raised."

    def _why_happened(self, info: Optional[dict[str, Any]], exc_type: str) -> str:
        if info and info.get("why_it_happens"):
            return str(info["why_it_happens"])
        return "The operation encountered a condition it could not handle."

    def _simple_explanation(self, info: Optional[dict[str, Any]], exc_type: str) -> str:
        if info and info.get("simple_explanation"):
            return str(info["simple_explanation"])
        return f"An error of type {exc_type} occurred. Check the error message for details."

    def _analogy(self, info: Optional[dict[str, Any]], exc_type: str) -> str:
        if info and info.get("analogy"):
            return str(info["analogy"])
        return "No analogy available for this exception type."

    def _common_causes(self, info: Optional[dict[str, Any]]) -> str:
        if info and info.get("common_causes"):
            return str(info["common_causes"])
        return "Check the surrounding code and variable types."

    def _how_to_avoid(self, info: Optional[dict[str, Any]]) -> str:
        if info and info.get("fixes"):
            return str(info["fixes"])
        return "Review the error message and the highlighted line."

    def _difficulty(self, info: Optional[dict[str, Any]]) -> int:
        if info and "difficulty" in info:
            return int(info["difficulty"])
        return 1

    def _docs_reference(self, info: Optional[dict[str, Any]], exc_type: str) -> str:
        if info and info.get("docs_url"):
            return str(info["docs_url"])
        anchor = exc_type.lower()
        return f"https://docs.python.org/3/library/exceptions.html#{anchor}"

    def _root_cause(self, trace: TraceResult) -> dict[str, Any]:
        """Extract root-cause location from the innermost non-stdlib frame."""
        if not trace.frames:
            return {}

        # Prefer the innermost user frame (not a stdlib/site-packages frame)
        frame = trace.innermost_frame
        for f in reversed(trace.frames):
            fn = f.filename.replace("\\", "/")
            if "site-packages" not in fn and "<frozen" not in fn:
                frame = f
                break

        if frame is None:
            return {}

        return {
            "file": frame.filename,
            "short_file": frame.short_filename,
            "line": frame.lineno,
            "function": frame.function,
            "code": frame.code_context or "",
            "locals": frame.locals,
            "module": frame.module,
        }
