"""Trace collection and stack frame analysis."""

from __future__ import annotations

import linecache
import logging
import traceback
from dataclasses import dataclass, field
from types import FrameType, TracebackType
from typing import Optional

from .utils import safe_repr

logger = logging.getLogger(__name__)


@dataclass
class StackFrame:
    """A single captured stack frame.

    Attributes:
        filename: Source file path.
        lineno: Line number within the file.
        function: Enclosing function or method name.
        code_context: The source line at the error position (stripped).
        locals: Mapping of local variable names to their safe ``repr`` strings.
        module: Module name if available.
    """

    filename: str
    lineno: int
    function: str
    code_context: Optional[str] = None
    locals: dict[str, str] = field(default_factory=dict)
    module: str = ""

    def __post_init__(self) -> None:
        if self.code_context is None:
            self.code_context = self._fetch_source_line()

    def _fetch_source_line(self) -> Optional[str]:
        """Return the source line from the file cache."""
        if self.filename and self.filename not in ("<stdin>", "<string>"):
            line = linecache.getline(self.filename, self.lineno)
            if line:
                return line.rstrip()
        return None

    @property
    def short_filename(self) -> str:
        """Return the last two path components for compact display."""
        parts = self.filename.replace("\\", "/").split("/")
        return "/".join(parts[-2:]) if len(parts) >= 2 else self.filename


@dataclass
class TraceResult:
    """Structured result of a captured exception.

    Attributes:
        exception_type: Class name of the exception (e.g. ``"TypeError"``).
        exception_message: String representation of the exception value.
        exception_repr: Full ``repr()`` of the exception value.
        frames: Ordered list of :class:`StackFrame` objects (outermost first).
        full_traceback: The raw formatted traceback string.
        chained_cause: Optional chained ``__cause__`` or ``__context__`` TraceResult.
    """

    exception_type: str
    exception_message: str
    exception_repr: str
    frames: list[StackFrame]
    full_traceback: str
    chained_cause: Optional["TraceResult"] = None

    @property
    def innermost_frame(self) -> Optional[StackFrame]:
        """The last (innermost) frame – closest to where the error occurred."""
        return self.frames[-1] if self.frames else None

    @property
    def outermost_frame(self) -> Optional[StackFrame]:
        """The first (outermost) frame – the program entry point."""
        return self.frames[0] if self.frames else None


class TraceCollector:
    """Collects and structures exception traceback information."""

    MAX_LOCALS: int = 30

    def collect_from_exception(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Optional[TracebackType],
    ) -> TraceResult:
        """Collect a :class:`TraceResult` from an active exception.

        Args:
            exc_type: The exception class.
            exc_value: The exception instance.
            exc_tb: The traceback object (may be ``None``).

        Returns:
            Fully populated :class:`TraceResult`.
        """
        frames = self._collect_frames(exc_tb)
        full_trace = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        chained: Optional[TraceResult] = None
        cause = getattr(exc_value, "__cause__", None) or getattr(exc_value, "__context__", None)
        if cause is not None and cause is not exc_value:
            try:
                chained = self.collect_from_exception(
                    type(cause),
                    cause,
                    cause.__traceback__,
                )
            except Exception:  # noqa: BLE001
                pass

        return TraceResult(
            exception_type=exc_type.__name__,
            exception_message=str(exc_value),
            exception_repr=safe_repr(exc_value),
            frames=frames,
            full_traceback=full_trace,
            chained_cause=chained,
        )

    def _collect_frames(self, exc_tb: Optional[TracebackType]) -> list[StackFrame]:
        frames: list[StackFrame] = []
        tb = exc_tb
        while tb is not None:
            frame = tb.tb_frame
            lineno = tb.tb_lineno  # tb_lineno, not f_lineno, correctly handles re-raises
            frames.append(self._extract_frame(frame, lineno))
            tb = tb.tb_next
        return frames

    def _extract_frame(self, frame: FrameType, lineno: int) -> StackFrame:
        """Extract information from a single CPython frame object."""
        filename: str = frame.f_code.co_filename
        function: str = frame.f_code.co_name
        module: str = frame.f_globals.get("__name__", "")

        locals_dict: dict[str, str] = {}
        for idx, (k, v) in enumerate(frame.f_locals.items()):
            if idx >= self.MAX_LOCALS:
                locals_dict["…"] = f"({len(frame.f_locals) - self.MAX_LOCALS} more variables)"
                break
            locals_dict[k] = safe_repr(v)

        return StackFrame(
            filename=filename,
            lineno=lineno,
            function=function,
            locals=locals_dict,
            module=module,
        )
