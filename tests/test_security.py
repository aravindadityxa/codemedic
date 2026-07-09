"""Tests for codemedic.security."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemedic.security import SecurityWarning, check_file, check_source


def warnings_with_code(source: str, code: str) -> list[SecurityWarning]:
    return [w for w in check_source(source) if w.code == code]


class TestEvalExec:
    def test_eval_flagged(self) -> None:
        ws = warnings_with_code("eval(user_input)", "SEC001")
        assert len(ws) >= 1

    def test_exec_flagged(self) -> None:
        ws = warnings_with_code("exec(user_code)", "SEC001")
        assert len(ws) >= 1

    def test_eval_severity_high(self) -> None:
        ws = warnings_with_code("eval(x)", "SEC001")
        assert all(w.severity == "high" for w in ws)

    def test_literal_eval_not_flagged(self) -> None:
        # ast.literal_eval is safe
        ws = check_source("import ast\nast.literal_eval(s)")
        codes = [w.code for w in ws]
        assert "SEC001" not in codes


class TestCommandInjection:
    def test_os_system_with_variable_flagged(self) -> None:
        ws = warnings_with_code("import os\nos.system(user_cmd)", "SEC002")
        assert len(ws) >= 1

    def test_os_system_with_literal_not_flagged(self) -> None:
        ws = warnings_with_code("import os\nos.system('ls -la')", "SEC002")
        assert len(ws) == 0

    def test_subprocess_with_variable_flagged(self) -> None:
        ws = warnings_with_code("import subprocess\nsubprocess.run(cmd)", "SEC002")
        assert len(ws) >= 1


class TestPickle:
    def test_pickle_loads_flagged(self) -> None:
        ws = warnings_with_code("import pickle\npickle.loads(data)", "SEC003")
        assert len(ws) >= 1

    def test_pickle_load_flagged(self) -> None:
        ws = warnings_with_code("import pickle\npickle.load(f)", "SEC003")
        assert len(ws) >= 1

    def test_pickle_severity_high(self) -> None:
        ws = warnings_with_code("import pickle\npickle.loads(data)", "SEC003")
        assert all(w.severity == "high" for w in ws)


class TestPathTraversal:
    def test_dynamic_open_flagged(self) -> None:
        ws = warnings_with_code("open(user_path, 'r')", "SEC004")
        assert len(ws) >= 1

    def test_literal_open_not_flagged(self) -> None:
        ws = warnings_with_code("open('data.txt', 'r')", "SEC004")
        assert len(ws) == 0


class TestWeakHashing:
    def test_md5_flagged(self) -> None:
        ws = warnings_with_code("import hashlib\nhashlib.md5(data)", "SEC005")
        assert len(ws) >= 1

    def test_sha1_flagged(self) -> None:
        ws = warnings_with_code("import hashlib\nhashlib.sha1(data)", "SEC005")
        assert len(ws) >= 1

    def test_sha256_not_flagged(self) -> None:
        ws = warnings_with_code("import hashlib\nhashlib.sha256(data)", "SEC005")
        assert len(ws) == 0


class TestHardcodedSecrets:
    def test_password_flagged(self) -> None:
        ws = warnings_with_code("password = 'secret123'", "SEC007")
        assert len(ws) >= 1

    def test_api_key_flagged(self) -> None:
        ws = warnings_with_code("api_key = 'abc123def456'", "SEC007")
        assert len(ws) >= 1

    def test_severity_high(self) -> None:
        ws = warnings_with_code("password = 'hunter2'", "SEC007")
        assert all(w.severity == "high" for w in ws)


class TestInsecureProtocols:
    def test_telnetlib_flagged(self) -> None:
        ws = warnings_with_code("import telnetlib", "SEC006")
        assert len(ws) >= 1


class TestCleanCode:
    def test_clean_code_no_warnings(self) -> None:
        clean = "x = 1 + 2\nprint(x)\n"
        ws = check_source(clean)
        assert ws == []


class TestCheckFile:
    def test_check_file_clean(self, tmp_path: Path) -> None:
        p = tmp_path / "clean.py"
        p.write_text("x = 1\n")
        ws = check_file(p)
        assert ws == []

    def test_check_file_with_issues(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.py"
        p.write_text("eval(user_input)\n")
        ws = check_file(p)
        assert len(ws) >= 1

    def test_syntax_error_no_crash(self, tmp_path: Path) -> None:
        p = tmp_path / "syntax.py"
        p.write_text("def foo(:\n    pass\n")
        ws = check_file(p)
        # Should return empty list, not crash
        assert isinstance(ws, list)


class TestSecurityWarning:
    def test_attributes(self) -> None:
        w = SecurityWarning(
            line=10,
            column=4,
            code="SEC001",
            severity="high",
            message="eval() is dangerous",
            recommendation="Use ast.literal_eval()",
        )
        assert w.line == 10
        assert w.code == "SEC001"
        assert w.severity == "high"
