"""Security checks for Python source code.

Detects patterns that are commonly associated with security vulnerabilities
and warns the user.  No code is executed during analysis.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


@dataclass
class SecurityWarning:
    """A single security warning produced by :class:`SecurityChecker`.

    Attributes:
        line: Source line number (1-based).
        column: Column offset (0-based).
        code: Short machine-readable identifier (e.g. ``"SEC001"``).
        severity: ``"low"``, ``"medium"``, or ``"high"``.
        message: Human-readable description.
        recommendation: How to address the issue.
    """

    line: int
    column: int
    code: str
    severity: str
    message: str
    recommendation: str


_HARDCODED_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("password", re.compile(r'(?i)password\s*=\s*["\'][^"\']{3,}["\']')),
    ("secret", re.compile(r'(?i)secret\s*=\s*["\'][^"\']{3,}["\']')),
    ("api_key", re.compile(r'(?i)api[_-]?key\s*=\s*["\'][^"\']{3,}["\']')),
    ("token", re.compile(r'(?i)token\s*=\s*["\'][^"\']{8,}["\']')),
    ("private_key", re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
]


class SecurityChecker(ast.NodeVisitor):
    """AST-based security scanner."""

    def __init__(self) -> None:
        self.warnings: list[SecurityWarning] = []

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._get_func_name(node)

        if func_name in ("eval", "exec"):
            self.warnings.append(SecurityWarning(
                line=node.lineno,
                column=node.col_offset,
                code="SEC001",
                severity="high",
                message=f"Use of '{func_name}()' is a security risk.",
                recommendation=(
                    "Avoid eval/exec with untrusted input. "
                    "Use ast.literal_eval() for safe literal parsing."
                ),
            ))

        if func_name in ("os.system", "subprocess.call", "subprocess.run",
                         "subprocess.Popen", "os.popen"):
            # Check if argument is not a plain string literal (injection risk)
            if node.args and not isinstance(node.args[0], ast.Constant):
                self.warnings.append(SecurityWarning(
                    line=node.lineno,
                    column=node.col_offset,
                    code="SEC002",
                    severity="medium",
                    message=(
                        f"Potential command injection via '{func_name}' "
                        "with dynamic argument."
                    ),
                    recommendation=(
                        "Pass a list of arguments instead of a shell string. "
                        "Use subprocess.run([...], shell=False)."
                    ),
                ))

        if func_name in ("pickle.loads", "pickle.load", "shelve.open"):
            self.warnings.append(SecurityWarning(
                line=node.lineno,
                column=node.col_offset,
                code="SEC003",
                severity="high",
                message=(
                    f"'{func_name}' can execute arbitrary code when "
                    "deserialising untrusted data."
                ),
                recommendation=(
                    "Never unpickle data from untrusted sources. "
                    "Use JSON instead."
                ),
            ))

        if func_name in ("open", "io.open"):
            # path traversal hint
            if node.args and not isinstance(node.args[0], ast.Constant):
                self.warnings.append(SecurityWarning(
                    line=node.lineno,
                    column=node.col_offset,
                    code="SEC004",
                    severity="low",
                    message=(
                        "Dynamic path passed to open() – "
                        "verify it is sanitised."
                    ),
                    recommendation=(
                        "Use pathlib.Path.resolve() and check that the "
                        "resolved path is within the intended directory."
                    ),
                ))

        if func_name in ("hashlib.md5", "hashlib.sha1"):
            self.warnings.append(SecurityWarning(
                line=node.lineno,
                column=node.col_offset,
                code="SEC005",
                severity="medium",
                message=f"'{func_name}' uses a weak hashing algorithm.",
                recommendation="Use hashlib.sha256() or stronger for security-sensitive operations.",
            ))

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in ("telnetlib", "ftplib"):
                self.warnings.append(SecurityWarning(
                    line=node.lineno,
                    column=node.col_offset,
                    code="SEC006",
                    severity="medium",
                    message=f"'{alias.name}' uses unencrypted protocols.",
                    recommendation="Prefer SSH (paramiko) or SFTP for secure communication.",
                ))
        self.generic_visit(node)

    @staticmethod
    def _get_func_name(node: ast.Call) -> str:
        """Extract a dotted function name from a Call node."""
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts: list[str] = []
            obj: ast.expr = func
            while isinstance(obj, ast.Attribute):
                parts.append(obj.attr)
                obj = obj.value
            if isinstance(obj, ast.Name):
                parts.append(obj.id)
            return ".".join(reversed(parts))
        return ""


def check_file(filepath: Union[str, Path]) -> list[SecurityWarning]:
    """Run security checks on a Python source file.

    Args:
        filepath: Path to the ``.py`` file.

    Returns:
        List of :class:`SecurityWarning` objects (empty if none found).
    """
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    return check_source(source, filename=str(path))


def check_source(source: str, filename: str = "<string>") -> list[SecurityWarning]:
    """Run security checks on a Python source string.

    Args:
        source: Python source code.
        filename: Filename for error reporting.

    Returns:
        List of :class:`SecurityWarning` objects.
    """
    warnings: list[SecurityWarning] = []

    # AST-based checks
    try:
        tree = ast.parse(source, filename)
    except SyntaxError:
        return warnings  # syntax errors reported elsewhere

    checker = SecurityChecker()
    checker.visit(tree)
    warnings.extend(checker.warnings)

    # Regex-based secret detection (line-by-line)
    for lineno, line in enumerate(source.splitlines(), 1):
        for label, pattern in _HARDCODED_SECRET_PATTERNS:
            if pattern.search(line):
                warnings.append(SecurityWarning(
                    line=lineno,
                    column=0,
                    code="SEC007",
                    severity="high",
                    message=f"Possible hardcoded {label} detected.",
                    recommendation=(
                        "Store secrets in environment variables or a "
                        "secrets manager. Never commit credentials to "
                        "source control."
                    ),
                ))

    return warnings
