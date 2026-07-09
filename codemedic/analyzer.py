"""Static code analyser using the Python ``ast`` module.

Detects a wide range of code quality, correctness, and style issues without
executing the code.
"""

from __future__ import annotations

import ast
import builtins
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins))


@dataclass
class AnalysisIssue:
    """A single static analysis finding.

    Attributes:
        line: 1-based source line number.
        column: 0-based column offset.
        message: Human-readable description.
        severity: ``"error"``, ``"warning"``, or ``"info"``.
        category: Machine-readable category tag.
    """

    line: int
    column: int
    message: str
    severity: str
    category: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] Line {self.line}: {self.message} ({self.category})"


class CodeAnalyzer:
    """Analyses Python source code for quality and correctness issues.

    Usage::

        analyzer = CodeAnalyzer()
        issues = analyzer.analyze_file("script.py")
        for issue in issues:
            print(issue)
    """

    def __init__(self) -> None:
        self.issues: list[AnalysisIssue] = []

    def analyze_file(self, filepath: Union[str, Path]) -> list[AnalysisIssue]:
        """Analyse a Python source file."""
        path = Path(filepath)
        code = path.read_text(encoding="utf-8")
        return self.analyze_code(code, filename=str(path))

    def analyze_code(self, code: str, filename: str = "<string>") -> list[AnalysisIssue]:
        """Analyse a Python source string, returning all issues found."""
        self.issues = []
        try:
            tree = ast.parse(code, filename)
        except SyntaxError as exc:
            self.issues.append(AnalysisIssue(
                line=exc.lineno or 0,
                column=exc.offset or 0,
                message=f"Syntax error: {exc.msg}",
                severity="error",
                category="syntax",
            ))
            return self.issues

        visitor = _AnalyzerVisitor(filename)
        visitor.visit(tree)
        self.issues.extend(visitor.issues)

        # Token-level checks that are easier outside the AST
        self._check_division_by_zero_literal(code)

        return self.issues

    def _check_division_by_zero_literal(self, code: str) -> None:
        """Flag literal ``/ 0`` or ``% 0`` patterns."""
        pattern = re.compile(r"[/%]\s*0\b")
        for lineno, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line):
                self.issues.append(AnalysisIssue(
                    line=lineno,
                    column=0,
                    message="Potential division by zero (literal 0 as divisor).",
                    severity="warning",
                    category="division_by_zero",
                ))


class _AnalyzerVisitor(ast.NodeVisitor):
    """Internal AST visitor that performs all static checks."""

    MAX_FUNCTION_LINES: int = 60
    MAX_NESTING_DEPTH: int = 5

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.issues: list[AnalysisIssue] = []
        self._function_names: set[str] = set()
        self._class_names: set[str] = set()

    def _add(
        self,
        node: ast.AST,
        message: str,
        severity: str,
        category: str,
        col: int = 0,
    ) -> None:
        line = getattr(node, "lineno", 0)
        col = getattr(node, "col_offset", col)
        self.issues.append(AnalysisIssue(
            line=line, column=col, message=message, severity=severity, category=category
        ))

    def visit_Module(self, node: ast.Module) -> None:
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)  # type: ignore[arg-type]

    def _check_function(self, node: ast.FunctionDef) -> None:
        if node.name in self._function_names:
            self._add(
                node,
                f"Duplicate function definition: '{node.name}'.",
                "warning",
                "duplicate_function",
            )
        self._function_names.add(node.name)

        if not (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            self._add(
                node,
                f"Function '{node.name}' is missing a docstring.",
                "info",
                "missing_docstring",
            )

        if node.returns is None and node.name not in ("__init__", "__new__"):
            self._add(
                node,
                f"Function '{node.name}' is missing a return type annotation.",
                "info",
                "missing_type_hint",
            )

        end_line = getattr(node, "end_lineno", node.lineno)
        func_len = end_line - node.lineno
        if func_len > self.MAX_FUNCTION_LINES:
            self._add(
                node,
                (
                    f"Function '{node.name}' is {func_len} lines long "
                    f"(>{self.MAX_FUNCTION_LINES}). Consider refactoring."
                ),
                "warning",
                "long_function",
            )

        for default in node.args.defaults + node.args.kw_defaults:
            if default is not None and isinstance(
                default, (ast.List, ast.Dict, ast.Set)
            ):
                self._add(
                    node,
                    (
                        f"Function '{node.name}' uses a mutable default "
                        "argument. Use None and initialise inside."
                    ),
                    "warning",
                    "mutable_default_arg",
                )

        self._check_unused_vars(node)
        self._check_recursion_risk(node)

        for child in node.body:
            self._check_nesting(child, depth=0)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in self._class_names:
            self._add(
                node,
                f"Duplicate class definition: '{node.name}'.",
                "warning",
                "duplicate_class",
            )
        self._class_names.add(node.name)

        if not (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            self._add(
                node,
                f"Class '{node.name}' is missing a docstring.",
                "info",
                "missing_docstring",
            )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(
                node,
                (
                    "Bare 'except:' clause catches all exceptions including "
                    "SystemExit and KeyboardInterrupt. Use 'except Exception:'."
                ),
                "warning",
                "bare_except",
            )

        # Empty except body (only 'pass' or ellipsis)
        if all(isinstance(stmt, (ast.Pass, ast.Expr)) for stmt in node.body):
            body_strs = [ast.dump(s) for s in node.body]
            if all("Pass" in s or "Constant(value=Ellipsis" in s for s in body_strs):
                self._add(
                    node,
                    "Empty except block silently swallows exceptions.",
                    "warning",
                    "empty_except",
                )

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                self._add(
                    node,
                    (
                        f"Wildcard import 'from {node.module} import *' "
                        "pollutes the namespace."
                    ),
                    "warning",
                    "wildcard_import",
                )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        self.generic_visit(node)

    def _check_unused_vars(self, func_node: ast.FunctionDef) -> None:
        assigned: dict[str, int] = {}  # name -> first assignment line
        used: set[str] = set()

        for child in ast.walk(func_node):
            if isinstance(child, ast.Name):
                if isinstance(child.ctx, ast.Store):
                    if child.id not in assigned:
                        assigned[child.id] = getattr(child, "lineno", func_node.lineno)
                elif isinstance(child.ctx, ast.Load):
                    used.add(child.id)

        # Include function params as "assigned"
        for arg in func_node.args.args + func_node.args.posonlyargs + func_node.args.kwonlyargs:
            assigned[arg.arg] = func_node.lineno
        if func_node.args.vararg:
            assigned[func_node.args.vararg.arg] = func_node.lineno
        if func_node.args.kwarg:
            assigned[func_node.args.kwarg.arg] = func_node.lineno

        unused = set(assigned) - used - _BUILTIN_NAMES - {"self", "cls", "_"}
        unused = {n for n in unused if not n.startswith("_")}

        for name in unused:
            self.issues.append(AnalysisIssue(
                line=assigned[name],
                column=0,
                message=f"Variable '{name}' is assigned but never used.",
                severity="warning",
                category="unused_variable",
            ))

    def _check_recursion_risk(self, func_node: ast.FunctionDef) -> None:
        """Warn if a function calls itself with no conditional guard.

        A function is considered risky when it calls itself recursively but
        the recursive call is not protected by any ``if``/``elif`` conditional
        that could act as a base case.
        """
        calls_self = False
        has_conditional_guard = False

        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                name = ""
                if isinstance(child.func, ast.Name):
                    name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    name = child.func.attr
                if name == func_node.name:
                    calls_self = True
            # An If node at the top level of the function body is a guard.
            if isinstance(child, ast.If):
                has_conditional_guard = True

        if calls_self and not has_conditional_guard:
            self._add(
                func_node,
                (
                    f"Function '{func_node.name}' calls itself with no "
                    "conditional guard – potential infinite recursion."
                ),
                "warning",
                "infinite_recursion_risk",
            )

    def _check_nesting(self, node: ast.AST, depth: int) -> None:
        if depth > self.MAX_NESTING_DEPTH:
            self.issues.append(AnalysisIssue(
                line=getattr(node, "lineno", 0),
                column=0,
                message=(
                    f"Code nesting depth exceeds {self.MAX_NESTING_DEPTH} "
                    "levels. Consider extracting into functions."
                ),
                severity="warning",
                category="deep_nesting",
            ))
            return
        nesting_nodes = (
            ast.If,
            ast.For,
            ast.While,
            ast.With,
            ast.Try,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        )
        if isinstance(node, nesting_nodes):
            for child in ast.iter_child_nodes(node):
                self._check_nesting(child, depth + 1)
