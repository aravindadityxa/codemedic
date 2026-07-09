"""Tests for codemedic.trace."""

from __future__ import annotations

import pytest

from codemedic.trace import StackFrame, TraceCollector, TraceResult


def _collect(exc: Exception) -> TraceResult:
    collector = TraceCollector()
    return collector.collect_from_exception(type(exc), exc, exc.__traceback__)


class TestStackFrame:
    def test_basic_attributes(self) -> None:
        frame = StackFrame(filename="test.py", lineno=10, function="my_func")
        assert frame.filename == "test.py"
        assert frame.lineno == 10
        assert frame.function == "my_func"

    def test_short_filename_two_parts(self) -> None:
        frame = StackFrame(filename="/a/b/c/module.py", lineno=1, function="f")
        assert frame.short_filename == "c/module.py"

    def test_short_filename_single(self) -> None:
        frame = StackFrame(filename="script.py", lineno=1, function="f")
        assert frame.short_filename == "script.py"

    def test_locals_default_empty(self) -> None:
        frame = StackFrame(filename="test.py", lineno=1, function="f")
        assert frame.locals == {}

    def test_code_context_none_for_string(self) -> None:
        # For "<string>" filename, code_context should stay None
        frame = StackFrame(filename="<string>", lineno=1, function="f")
        assert frame.code_context is None


class TestTraceResult:
    def test_innermost_frame(self, type_error_trace: TraceResult) -> None:
        assert type_error_trace.innermost_frame is not None
        assert isinstance(type_error_trace.innermost_frame, StackFrame)

    def test_outermost_frame(self, type_error_trace: TraceResult) -> None:
        assert type_error_trace.outermost_frame is not None

    def test_no_frames_returns_none(self) -> None:
        tr = TraceResult(
            exception_type="TestError",
            exception_message="test",
            exception_repr="TestError()",
            frames=[],
            full_traceback="",
        )
        assert tr.innermost_frame is None
        assert tr.outermost_frame is None

    def test_chained_cause_default_none(self, type_error_trace: TraceResult) -> None:
        assert type_error_trace.chained_cause is None


class TestTraceCollector:
    def test_collect_type_error(self, type_error_trace: TraceResult) -> None:
        assert type_error_trace.exception_type == "TypeError"
        assert (
            "str" in type_error_trace.exception_message.lower()
            or "int" in type_error_trace.exception_message.lower()
        )
        assert len(type_error_trace.frames) >= 1
        assert len(type_error_trace.full_traceback) > 0

    def test_collect_name_error(self, name_error_trace: TraceResult) -> None:
        assert name_error_trace.exception_type == "NameError"
        assert len(name_error_trace.frames) >= 1

    def test_collect_index_error(self, index_error_trace: TraceResult) -> None:
        assert index_error_trace.exception_type == "IndexError"

    def test_collect_key_error(self, key_error_trace: TraceResult) -> None:
        assert key_error_trace.exception_type == "KeyError"

    def test_collect_zero_div(self, zero_div_trace: TraceResult) -> None:
        assert zero_div_trace.exception_type == "ZeroDivisionError"

    def test_frame_has_locals(self) -> None:
        my_var = 42  # noqa: F841
        try:
            _ = 1 / 0
        except ZeroDivisionError as exc:
            trace = _collect(exc)
        # locals should be captured
        assert isinstance(trace.frames[-1].locals, dict)

    def test_repr_captured(self, type_error_trace: TraceResult) -> None:
        assert type_error_trace.exception_repr != ""

    def test_chained_exception(self) -> None:
        try:
            try:
                raise ValueError("original")
            except ValueError as inner:
                raise RuntimeError("wrapper") from inner
        except RuntimeError as exc:
            trace = _collect(exc)
        assert trace.exception_type == "RuntimeError"
        # chained cause should be captured
        assert trace.chained_cause is not None
        assert trace.chained_cause.exception_type == "ValueError"

    def test_max_locals_limit(self) -> None:
        """Collector should not crash when a frame has many locals."""
        try:
            # Create a frame with many locals
            code = (
                "; ".join(f"var_{i} = {i}" for i in range(50)) + "; raise ValueError('many locals')"
            )
            exec(code)  # noqa: S102
        except ValueError as exc:
            trace = _collect(exc)
        assert len(trace.frames) >= 1
