"""Tests for codemedic.fixer."""

from __future__ import annotations

import pytest

from codemedic.fixer import Fixer, PatchSuggestion
from codemedic.trace import TraceCollector, TraceResult


def collect(exc: Exception) -> TraceResult:
    c = TraceCollector()
    return c.collect_from_exception(type(exc), exc, exc.__traceback__)


class TestPatchSuggestion:
    def test_to_dict(self) -> None:
        ps = PatchSuggestion(
            line_number=5,
            original_line="print('Age: ' + 25)",
            suggested_line="print('Age: ' + str(25))",
            description="Convert to str",
            confidence=0.9,
        )
        d = ps.to_dict()
        assert d["line_number"] == 5
        assert d["confidence"] == 0.9
        assert d["description"] == "Convert to str"

    def test_diff_property(self) -> None:
        ps = PatchSuggestion(
            line_number=1,
            original_line="old code",
            suggested_line="new code",
            description="test",
            confidence=0.8,
        )
        diff = ps.diff
        assert isinstance(diff, str)

    def test_confidence_rounded(self) -> None:
        ps = PatchSuggestion(1, "a", "b", "test", 0.856789)
        assert ps.to_dict()["confidence"] == 0.86


class TestFixer:
    def test_type_error_string_concat(self, type_error_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(type_error_trace)
        assert len(fixes) >= 1
        assert all(isinstance(f, PatchSuggestion) for f in fixes)

    def test_sorted_by_confidence(self, type_error_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(type_error_trace)
        if len(fixes) >= 2:
            for i in range(len(fixes) - 1):
                assert fixes[i].confidence >= fixes[i + 1].confidence

    def test_name_error_similar_name(self) -> None:
        try:
            exec("messge = 'hi'\nprint(message)")  # noqa: S102
        except NameError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1

    def test_index_error_literal(self, index_error_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(index_error_trace)
        assert len(fixes) >= 1

    def test_key_error_suggests_get(self, key_error_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(key_error_trace)
        assert len(fixes) >= 1
        # Should mention .get() either in the description or in the suggested line
        combined = " ".join(f.description + str(f.suggested_line) for f in fixes)
        assert ".get(" in combined or "dict.get" in combined

    def test_zero_division_fix(self, zero_div_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(zero_div_trace)
        assert len(fixes) >= 1

    def test_attribute_error_fix(self, attr_error_trace: TraceResult) -> None:
        fixer = Fixer()
        fixes = fixer.suggest_fixes(attr_error_trace)
        assert len(fixes) >= 1

    def test_import_error(self) -> None:
        try:
            import nonexistent_module_xyz  # noqa: F401
        except ImportError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1
        assert any("pip install" in f.description for f in fixes)

    def test_recursion_error(self) -> None:
        # Raise RecursionError directly to avoid actually exhausting the stack
        try:
            raise RecursionError("maximum recursion depth exceeded")
        except RecursionError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1

    def test_value_error_fix(self) -> None:
        try:
            int("not a number")
        except ValueError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1

    def test_file_not_found_fix(self) -> None:
        try:
            open("definitely_not_a_real_file_xyz_abc.txt")
        except FileNotFoundError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1

    def test_generic_fallback_for_unknown(self) -> None:
        """RuntimeError should still produce a generic suggestion."""
        try:
            raise RuntimeError("Custom error message")
        except RuntimeError as exc:
            trace = collect(exc)
        fixer = Fixer()
        fixes = fixer.suggest_fixes(trace)
        assert len(fixes) >= 1

    def test_all_suggestions_have_description(self, type_error_trace: TraceResult) -> None:
        fixer = Fixer()
        for fix in fixer.suggest_fixes(type_error_trace):
            assert fix.description, "PatchSuggestion.description must not be empty"

    def test_confidence_in_range(self, type_error_trace: TraceResult) -> None:
        fixer = Fixer()
        for fix in fixer.suggest_fixes(type_error_trace):
            assert 0.0 <= fix.confidence <= 1.0
