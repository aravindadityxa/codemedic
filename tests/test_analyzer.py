"""Tests for codemedic.analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemedic.analyzer import AnalysisIssue, CodeAnalyzer


def issues_of(code: str, category: str | None = None) -> list[AnalysisIssue]:
    analyzer = CodeAnalyzer()
    all_issues = analyzer.analyze_code(code)
    if category:
        return [i for i in all_issues if i.category == category]
    return all_issues


class TestAnalysisIssue:
    def test_str_representation(self) -> None:
        issue = AnalysisIssue(line=5, column=0, message="Test msg", severity="warning", category="test")
        s = str(issue)
        assert "WARNING" in s
        assert "Line 5" in s
        assert "Test msg" in s


class TestSyntaxError:
    def test_syntax_error_detected(self) -> None:
        issues = issues_of("def foo(:\n    pass", "syntax")
        assert len(issues) >= 1
        assert issues[0].severity == "error"

    def test_valid_code_no_syntax_error(self) -> None:
        issues = issues_of("x = 1 + 2", "syntax")
        assert len(issues) == 0


class TestUnusedVariable:
    def test_unused_variable_detected(self) -> None:
        code = "def foo():\n    x = 5\n    return 10\n"
        found = issues_of(code, "unused_variable")
        assert any("x" in i.message for i in found)

    def test_used_variable_not_flagged(self) -> None:
        code = "def foo():\n    x = 5\n    return x\n"
        found = issues_of(code, "unused_variable")
        assert not any("x" in i.message for i in found)

    def test_underscore_not_flagged(self) -> None:
        code = "def foo():\n    _ = compute()\n    return 1\n"
        # _ is a convention for intentionally unused
        found = issues_of(code, "unused_variable")
        assert not any(i.message == "Variable '_' is assigned but never used." for i in found)

    def test_self_not_flagged(self) -> None:
        code = "class A:\n    def method(self):\n        return 42\n"
        found = issues_of(code, "unused_variable")
        assert not any("self" in i.message for i in found)


class TestDivisionByZero:
    def test_literal_division_flagged(self) -> None:
        found = issues_of("x = 1 / 0", "division_by_zero")
        assert len(found) >= 1

    def test_modulo_zero_flagged(self) -> None:
        found = issues_of("x = 10 % 0", "division_by_zero")
        assert len(found) >= 1

    def test_safe_division_not_flagged(self) -> None:
        found = issues_of("x = 10 / 5", "division_by_zero")
        assert len(found) == 0

    def test_comment_with_zero_not_flagged(self) -> None:
        found = issues_of("# x = 1 / 0  (example)", "division_by_zero")
        assert len(found) == 0


class TestBareExcept:
    def test_bare_except_flagged(self) -> None:
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        found = issues_of(code, "bare_except")
        assert len(found) >= 1

    def test_typed_except_not_flagged(self) -> None:
        code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        found = issues_of(code, "bare_except")
        assert len(found) == 0


class TestEmptyExcept:
    def test_empty_except_flagged(self) -> None:
        code = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        found = issues_of(code, "empty_except")
        assert len(found) >= 1

    def test_non_empty_except_not_flagged(self) -> None:
        code = "try:\n    x = 1\nexcept Exception as e:\n    print(e)\n"
        found = issues_of(code, "empty_except")
        assert len(found) == 0


class TestMissingDocstring:
    def test_function_without_docstring(self) -> None:
        code = "def my_function():\n    return 42\n"
        found = issues_of(code, "missing_docstring")
        assert any("my_function" in i.message for i in found)

    def test_function_with_docstring_not_flagged(self) -> None:
        code = 'def my_function():\n    """Do something."""\n    return 42\n'
        found = issues_of(code, "missing_docstring")
        assert not any("my_function" in i.message for i in found)

    def test_class_without_docstring(self) -> None:
        code = "class MyClass:\n    pass\n"
        found = issues_of(code, "missing_docstring")
        assert any("MyClass" in i.message for i in found)


class TestMutableDefaultArg:
    def test_list_default_flagged(self) -> None:
        code = "def foo(x=[]):\n    return x\n"
        found = issues_of(code, "mutable_default_arg")
        assert len(found) >= 1

    def test_dict_default_flagged(self) -> None:
        code = "def foo(x={}):\n    return x\n"
        found = issues_of(code, "mutable_default_arg")
        assert len(found) >= 1

    def test_none_default_not_flagged(self) -> None:
        code = "def foo(x=None):\n    return x\n"
        found = issues_of(code, "mutable_default_arg")
        assert len(found) == 0


class TestMissingTypeHint:
    def test_missing_return_type(self) -> None:
        code = "def foo():\n    return 42\n"
        found = issues_of(code, "missing_type_hint")
        assert any("foo" in i.message for i in found)

    def test_has_return_type_not_flagged(self) -> None:
        code = "def foo() -> int:\n    return 42\n"
        found = issues_of(code, "missing_type_hint")
        assert not any("foo" in i.message for i in found)

    def test_init_not_flagged(self) -> None:
        code = "class A:\n    def __init__(self):\n        pass\n"
        found = issues_of(code, "missing_type_hint")
        assert not any("__init__" in i.message for i in found)


class TestDuplicateFunctions:
    def test_duplicate_function(self) -> None:
        code = "def foo():\n    pass\n\ndef foo():\n    pass\n"
        found = issues_of(code, "duplicate_function")
        assert len(found) >= 1

    def test_unique_functions_ok(self) -> None:
        code = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        found = issues_of(code, "duplicate_function")
        assert len(found) == 0


class TestDuplicateClasses:
    def test_duplicate_class(self) -> None:
        code = "class Foo:\n    pass\n\nclass Foo:\n    pass\n"
        found = issues_of(code, "duplicate_class")
        assert len(found) >= 1


class TestWildcardImport:
    def test_wildcard_import_flagged(self) -> None:
        code = "from os import *\n"
        found = issues_of(code, "wildcard_import")
        assert len(found) >= 1

    def test_normal_import_not_flagged(self) -> None:
        code = "from os import path\n"
        found = issues_of(code, "wildcard_import")
        assert len(found) == 0


class TestLongFunction:
    def test_long_function_flagged(self) -> None:
        body = "\n".join(f"    x{i} = {i}" for i in range(70))
        code = f"def long_func():\n{body}\n"
        found = issues_of(code, "long_function")
        assert len(found) >= 1

    def test_short_function_not_flagged(self) -> None:
        code = "def short():\n    return 1\n"
        found = issues_of(code, "long_function")
        assert len(found) == 0


class TestRecursionRisk:
    def test_no_base_case_flagged(self) -> None:
        code = "def infinite(n):\n    return infinite(n - 1)\n"
        found = issues_of(code, "infinite_recursion_risk")
        assert len(found) >= 1

    def test_with_base_case_not_flagged(self) -> None:
        code = "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n"
        found = issues_of(code, "infinite_recursion_risk")
        assert len(found) == 0


class TestAnalyzeFile:
    def test_analyze_real_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.py"
        p.write_text("def foo():\n    x = 5\n    return 10\n", encoding="utf-8")
        analyzer = CodeAnalyzer()
        issues = analyzer.analyze_file(p)
        assert isinstance(issues, list)

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.py"
        p.write_text("", encoding="utf-8")
        analyzer = CodeAnalyzer()
        issues = analyzer.analyze_file(p)
        assert isinstance(issues, list)
