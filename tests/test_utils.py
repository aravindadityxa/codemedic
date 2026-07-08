"""Tests for codemedic.utils."""

from __future__ import annotations

import logging

import pytest

from codemedic.utils import (
    get_version,
    indent,
    safe_repr,
    setup_logging,
    truncate_string,
)


class TestGetVersion:
    def test_returns_string(self) -> None:
        v = get_version()
        assert isinstance(v, str)
        assert len(v) > 0

    def test_format(self) -> None:
        v = get_version()
        parts = v.split(".")
        assert len(parts) >= 2, f"Version should be semver, got: {v}"


class TestTruncateString:
    def test_short_string_unchanged(self) -> None:
        assert truncate_string("hello", 100) == "hello"

    def test_long_string_truncated(self) -> None:
        s = "a" * 300
        result = truncate_string(s, 200)
        assert len(result) < 300
        assert "truncated" in result

    def test_exact_limit_unchanged(self) -> None:
        s = "x" * 200
        assert truncate_string(s, 200) == s

    def test_default_limit(self) -> None:
        s = "z" * 201
        result = truncate_string(s)
        assert "truncated" in result


class TestSafeRepr:
    def test_normal_object(self) -> None:
        assert safe_repr(42) == "42"

    def test_string(self) -> None:
        assert safe_repr("hello") == "'hello'"

    def test_list(self) -> None:
        assert "1" in safe_repr([1, 2, 3])

    def test_truncation(self) -> None:
        long_list = list(range(1000))
        result = safe_repr(long_list, max_len=50)
        assert len(result) <= 65  # 50 + ellipsis

    def test_unrepresentable(self) -> None:
        class Bad:
            def __repr__(self) -> str:
                raise RuntimeError("repr broken")

        result = safe_repr(Bad())
        assert result == "<unrepresentable>"


class TestSetupLogging:
    def test_sets_level(self) -> None:
        setup_logging(level=logging.DEBUG, force=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_log_file(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        log_file = tmp_path / "test.log"
        setup_logging(level=logging.INFO, log_file=log_file, force=True)
        logging.getLogger("test").info("hello from test")
        assert log_file.exists()


class TestIndent:
    def test_single_line(self) -> None:
        assert indent("hello") == "    hello"

    def test_multi_line(self) -> None:
        result = indent("line1\nline2")
        assert result == "    line1\n    line2"

    def test_custom_spaces(self) -> None:
        assert indent("x", 2) == "  x"
