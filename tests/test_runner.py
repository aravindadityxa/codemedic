"""Tests for codemedic.runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemedic.runner import Runner, RunResult


class TestRunCode:
    def test_success(self) -> None:
        runner = Runner()
        result = runner.run_code("x = 1 + 2")
        assert result.success is True
        assert result.error is None
        assert result.trace is None

    def test_captures_stdout(self) -> None:
        runner = Runner()
        result = runner.run_code("print('hello world')")
        assert result.success is True
        assert "hello world" in result.stdout

    def test_type_error(self) -> None:
        runner = Runner()
        result = runner.run_code('"hello" + 42')
        assert result.success is False
        assert result.trace is not None
        assert result.trace.exception_type == "TypeError"

    def test_name_error(self) -> None:
        runner = Runner()
        result = runner.run_code("print(undefined_variable_xyz)")
        assert result.success is False
        assert result.trace.exception_type == "NameError"

    def test_index_error(self) -> None:
        runner = Runner()
        result = runner.run_code("[1,2,3][99]")
        assert result.success is False
        assert result.trace.exception_type == "IndexError"

    def test_key_error(self) -> None:
        runner = Runner()
        result = runner.run_code("{'a':1}['missing']")
        assert result.success is False
        assert result.trace.exception_type == "KeyError"

    def test_zero_division(self) -> None:
        runner = Runner()
        result = runner.run_code("1 / 0")
        assert result.success is False
        assert result.trace.exception_type == "ZeroDivisionError"

    def test_attribute_error(self) -> None:
        runner = Runner()
        result = runner.run_code("(5).nonexistent_method()")
        assert result.success is False
        assert result.trace.exception_type == "AttributeError"

    def test_syntax_error(self) -> None:
        runner = Runner()
        result = runner.run_code("def foo(:")
        assert result.success is False
        assert result.trace.exception_type == "SyntaxError"

    def test_explanation_populated(self) -> None:
        runner = Runner()
        result = runner.run_code('"hello" + 42')
        assert result.explanation is not None
        assert result.explanation["error_type"] == "TypeError"
        assert len(result.explanation["simple_explanation"]) > 0

    def test_fixes_generated(self) -> None:
        runner = Runner()
        result = runner.run_code('"hello" + 42')
        assert len(result.fixes) >= 1

    def test_analysis_populated(self) -> None:
        runner = Runner()
        result = runner.run_code("x = 1 + 2\n1/0")
        assert isinstance(result.analysis, list)

    def test_runtime_error(self) -> None:
        runner = Runner()
        result = runner.run_code("raise RuntimeError('test error')")
        assert result.success is False
        assert result.trace.exception_type == "RuntimeError"

    def test_value_error(self) -> None:
        runner = Runner()
        result = runner.run_code("int('not a number')")
        assert result.success is False
        assert result.trace.exception_type == "ValueError"


class TestRunFile:
    def test_run_clean_file(self, clean_py_file: Path) -> None:
        runner = Runner()
        result = runner.run_file(clean_py_file)
        assert result.success is True

    def test_run_error_file(self, sample_py_file: Path) -> None:
        runner = Runner()
        result = runner.run_file(sample_py_file)
        assert result.success is False
        assert result.trace is not None

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        runner = Runner()
        with pytest.raises(FileNotFoundError):
            runner.run_file(tmp_path / "nonexistent.py")

    def test_stdout_captured_from_file(self, tmp_path: Path) -> None:
        p = tmp_path / "output.py"
        p.write_text("print('test output')\n")
        runner = Runner()
        result = runner.run_file(p)
        assert "test output" in result.stdout


class TestRunWithCapture:
    def test_success(self) -> None:
        runner = Runner()
        result = runner.run_with_capture(lambda: 1 + 1)
        assert result.success is True

    def test_captures_exception(self) -> None:
        def bad():
            raise TypeError("test type error")

        runner = Runner()
        result = runner.run_with_capture(bad)
        assert result.success is False
        assert result.trace.exception_type == "TypeError"

    def test_captures_kwargs(self) -> None:
        def add(a, b):
            return a + b

        runner = Runner()
        result = runner.run_with_capture(add, 1, b=2)
        assert result.success is True


class TestRunResultToDict:
    def test_success_to_dict(self) -> None:
        runner = Runner()
        result = runner.run_code("x = 1")
        d = result.to_dict()
        assert d["success"] is True
        assert d["error_type"] is None

    def test_error_to_dict(self) -> None:
        runner = Runner()
        result = runner.run_code("1/0")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error_type"] == "ZeroDivisionError"
        assert "fixes" in d
        assert isinstance(d["fixes"], list)

    def test_fixes_serialised(self) -> None:
        runner = Runner()
        result = runner.run_code('"a" + 1')
        d = result.to_dict()
        for fix in d["fixes"]:
            assert "line_number" in fix
            assert "confidence" in fix
            assert "description" in fix


class TestModes:
    def test_beginner_mode(self) -> None:
        runner = Runner(mode="beginner")
        result = runner.run_code('"a" + 1')
        assert result.explanation is not None
        assert "simple_explanation" in result.explanation

    def test_professional_mode(self) -> None:
        runner = Runner(mode="professional")
        result = runner.run_code('"a" + 1')
        assert "docs_reference" in result.explanation
        assert "full_traceback" in result.explanation
