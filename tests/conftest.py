"""Shared pytest fixtures for the CodeMedic test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemedic.config import Config
from codemedic.database import KnowledgeBase
from codemedic.trace import TraceCollector, TraceResult


def _collect_trace(exc: Exception) -> TraceResult:
    collector = TraceCollector()
    return collector.collect_from_exception(type(exc), exc, exc.__traceback__)


@pytest.fixture
def tmp_db(tmp_path: Path) -> KnowledgeBase:
    """Fresh KnowledgeBase backed by a temporary SQLite file."""
    return KnowledgeBase(db_path=tmp_path / "test_errors.db")


@pytest.fixture
def default_config() -> Config:
    return Config()


@pytest.fixture
def beginner_config() -> Config:
    return Config(mode="beginner", dark_mode=False)


@pytest.fixture
def professional_config() -> Config:
    return Config(mode="professional", dark_mode=False)


@pytest.fixture
def type_error_trace() -> TraceResult:
    try:
        _ = "Age: " + 25  # type: ignore[operator]
    except TypeError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected TypeError was not raised")


@pytest.fixture
def name_error_trace() -> TraceResult:
    try:
        eval("undefined_var_xyz")  # noqa: S307
    except NameError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected NameError was not raised")


@pytest.fixture
def index_error_trace() -> TraceResult:
    try:
        _ = [1, 2, 3][99]
    except IndexError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected IndexError was not raised")


@pytest.fixture
def key_error_trace() -> TraceResult:
    try:
        _ = {"a": 1}["missing_key"]
    except KeyError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected KeyError was not raised")


@pytest.fixture
def zero_div_trace() -> TraceResult:
    try:
        _ = 1 / 0
    except ZeroDivisionError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected ZeroDivisionError was not raised")


@pytest.fixture
def attr_error_trace() -> TraceResult:
    try:
        _ = (5).append(3)  # type: ignore[attr-defined]
    except AttributeError as exc:
        return _collect_trace(exc)
    pytest.fail("Expected AttributeError was not raised")


@pytest.fixture
def sample_py_file(tmp_path: Path) -> Path:
    p = tmp_path / "sample.py"
    p.write_text("result = 'hello' + 42\n", encoding="utf-8")
    return p


@pytest.fixture
def clean_py_file(tmp_path: Path) -> Path:
    p = tmp_path / "clean.py"
    p.write_text("x = 1 + 2\nprint(x)\n", encoding="utf-8")
    return p
