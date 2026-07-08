"""Tests for codemedic.database."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemedic.database import KnowledgeBase


class TestKnowledgeBase:
    def test_creates_db_file(self, tmp_path: Path) -> None:
        db = KnowledgeBase(db_path=tmp_path / "test.db")
        assert (tmp_path / "test.db").exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c" / "test.db"
        db = KnowledgeBase(db_path=nested)
        assert nested.exists()

    def test_default_entries_populated(self, tmp_db: KnowledgeBase) -> None:
        count = tmp_db.count_errors()
        assert count >= 30, f"Expected ≥30 entries, got {count}"

    def test_get_type_error(self, tmp_db: KnowledgeBase) -> None:
        info = tmp_db.get_error_info("TypeError")
        assert info is not None
        assert info["exception_type"] == "TypeError"
        assert len(info["description"]) > 0
        assert len(info["simple_explanation"]) > 0
        assert len(info["analogy"]) > 0

    def test_get_all_major_exceptions(self, tmp_db: KnowledgeBase) -> None:
        required = [
            "TypeError", "NameError", "IndexError", "KeyError",
            "AttributeError", "ZeroDivisionError", "FileNotFoundError",
            "ImportError", "ValueError", "RuntimeError", "RecursionError",
            "MemoryError", "OSError", "PermissionError", "SyntaxError",
        ]
        for exc_name in required:
            info = tmp_db.get_error_info(exc_name)
            assert info is not None, f"Missing entry for {exc_name}"

    def test_get_unknown_returns_none(self, tmp_db: KnowledgeBase) -> None:
        assert tmp_db.get_error_info("CompletelyFakeError") is None

    def test_get_all_errors_sorted(self, tmp_db: KnowledgeBase) -> None:
        all_errors = tmp_db.get_all_errors()
        names = [e["exception_type"] for e in all_errors]
        assert names == sorted(names)

    def test_add_error(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.add_error(
            exception_type="CustomError",
            description="Test error",
            simple_explanation="Simple test",
            analogy="Test analogy",
            fixes="Fix it",
            difficulty=2,
            category="test",
        )
        info = tmp_db.get_error_info("CustomError")
        assert info is not None
        assert info["description"] == "Test error"

    def test_add_error_replace(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.add_error("TypeError", description="Updated description")
        info = tmp_db.get_error_info("TypeError")
        assert info["description"] == "Updated description"

    def test_add_and_get_pattern(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.add_pattern("TypeError", r"\+ \d+", "Convert int to str()")
        patterns = tmp_db.get_patterns("TypeError")
        assert len(patterns) >= 1
        texts = [p[0] for p in patterns]
        assert r"\+ \d+" in texts

    def test_duplicate_pattern_ignored(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.add_pattern("ValueError", "pattern1", "suggestion1")
        tmp_db.add_pattern("ValueError", "pattern1", "suggestion1")
        patterns = tmp_db.get_patterns("ValueError")
        count = sum(1 for p in patterns if p[0] == "pattern1")
        assert count == 1

    def test_log_fix_attempt(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.log_fix_attempt("TypeError", "old code", "new code", feedback=1)
        history = tmp_db.get_fix_history("TypeError")
        assert len(history) >= 1
        assert history[0]["original_code"] == "old code"
        assert history[0]["fixed_code"] == "new code"

    def test_get_fix_history_all(self, tmp_db: KnowledgeBase) -> None:
        tmp_db.log_fix_attempt("TypeError", "a", "b")
        tmp_db.log_fix_attempt("NameError", "c", "d")
        history = tmp_db.get_fix_history()
        assert len(history) >= 2

    def test_count_errors(self, tmp_db: KnowledgeBase) -> None:
        count = tmp_db.count_errors()
        assert isinstance(count, int)
        assert count > 0

    def test_all_entries_have_docs_url(self, tmp_db: KnowledgeBase) -> None:
        for entry in tmp_db.get_all_errors():
            assert entry["docs_url"].startswith("https://"), (
                f"{entry['exception_type']} has invalid docs_url: {entry['docs_url']}"
            )

    def test_all_entries_have_difficulty(self, tmp_db: KnowledgeBase) -> None:
        for entry in tmp_db.get_all_errors():
            assert 1 <= entry["difficulty"] <= 3, (
                f"{entry['exception_type']} has invalid difficulty: {entry['difficulty']}"
            )
