"""Tests for codemedic.explanations."""

from __future__ import annotations

import pytest

from codemedic.database import KnowledgeBase
from codemedic.explanations import ExplanationEngine
from codemedic.trace import TraceCollector, TraceResult


def make_engine(mode: str = "beginner", tmp_db: KnowledgeBase | None = None) -> ExplanationEngine:
    return ExplanationEngine(knowledge_base=tmp_db, mode=mode)


class TestExplainTypeError:
    def test_returns_dict(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        engine = make_engine(tmp_db=tmp_db)
        result = engine.explain(type_error_trace)
        assert isinstance(result, dict)

    def test_error_type(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(type_error_trace)
        assert result["error_type"] == "TypeError"

    def test_has_simple_explanation(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(type_error_trace)
        assert "simple_explanation" in result
        assert len(result["simple_explanation"]) > 0

    def test_has_analogy(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(type_error_trace)
        assert "analogy" in result
        assert result["analogy"] != "No analogy available for this exception type."

    def test_has_root_cause(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(type_error_trace)
        assert "root_cause" in result
        assert isinstance(result["root_cause"], dict)

    def test_root_cause_has_line(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(type_error_trace)
        rc = result["root_cause"]
        assert "line" in rc
        assert isinstance(rc["line"], int)


class TestExplainModes:
    def test_professional_has_docs(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(mode="professional", tmp_db=tmp_db).explain(type_error_trace)
        assert "docs_reference" in result
        assert "TypeError" in result["docs_reference"].lower() or "docs.python.org" in result["docs_reference"]

    def test_professional_has_traceback(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(mode="professional", tmp_db=tmp_db).explain(type_error_trace)
        assert "full_traceback" in result
        assert len(result["full_traceback"]) > 0

    def test_beginner_no_traceback(self, type_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(mode="beginner", tmp_db=tmp_db).explain(type_error_trace)
        assert "full_traceback" not in result


class TestExplainByName:
    def test_type_error_by_name(self, tmp_db: KnowledgeBase) -> None:
        engine = make_engine(tmp_db=tmp_db)
        result = engine.explain_by_name("TypeError")
        assert result["error_type"] == "TypeError"
        assert len(result["simple_explanation"]) > 0

    def test_unknown_exception_graceful(self, tmp_db: KnowledgeBase) -> None:
        engine = make_engine(tmp_db=tmp_db)
        result = engine.explain_by_name("MadeUpError")
        assert result["error_type"] == "MadeUpError"
        # Should still return a valid dict with defaults
        assert "simple_explanation" in result

    def test_all_major_exceptions(self, tmp_db: KnowledgeBase) -> None:
        engine = make_engine(tmp_db=tmp_db)
        exceptions = [
            "TypeError", "NameError", "IndexError", "KeyError",
            "AttributeError", "ZeroDivisionError", "FileNotFoundError",
            "ValueError", "RuntimeError", "ImportError",
        ]
        for exc_name in exceptions:
            result = engine.explain_by_name(exc_name)
            assert result["error_type"] == exc_name, f"Wrong type for {exc_name}"
            assert result["simple_explanation"], f"Empty explanation for {exc_name}"


class TestVariousExceptions:
    def test_name_error(self, name_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(name_error_trace)
        assert result["error_type"] == "NameError"

    def test_index_error(self, index_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(index_error_trace)
        assert result["error_type"] == "IndexError"

    def test_key_error(self, key_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(key_error_trace)
        assert result["error_type"] == "KeyError"

    def test_zero_div(self, zero_div_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(zero_div_trace)
        assert result["error_type"] == "ZeroDivisionError"

    def test_attr_error(self, attr_error_trace: TraceResult, tmp_db: KnowledgeBase) -> None:
        result = make_engine(tmp_db=tmp_db).explain(attr_error_trace)
        assert result["error_type"] == "AttributeError"


class TestNoFrames:
    def test_empty_frames_root_cause_empty(self, tmp_db: KnowledgeBase) -> None:
        tr = TraceResult(
            exception_type="ValueError",
            exception_message="bad value",
            exception_repr="ValueError('bad value')",
            frames=[],
            full_traceback="",
        )
        result = make_engine(tmp_db=tmp_db).explain(tr)
        assert result["root_cause"] == {}
