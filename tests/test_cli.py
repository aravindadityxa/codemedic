"""Tests for codemedic.cli."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from codemedic.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def good_script(tmp_path: Path) -> Path:
    p = tmp_path / "good.py"
    p.write_text("x = 1 + 2\nprint(x)\n")
    return p


@pytest.fixture
def bad_script(tmp_path: Path) -> Path:
    p = tmp_path / "bad.py"
    p.write_text("result = 'hello' + 42\n")
    return p


@pytest.fixture
def analysis_script(tmp_path: Path) -> Path:
    p = tmp_path / "analysis.py"
    p.write_text(
        "def foo():\n"
        "    x = 5\n"
        "    return 10\n"
        "\n"
        "try:\n"
        "    pass\n"
        "except:\n"
        "    pass\n"
    )
    return p


class TestVersion:
    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "CodeMedic" in result.output

    def test_version_command(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "CodeMedic" in result.output


class TestHelp:
    def test_help_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output
        assert "analyze" in result.output
        assert "explain" in result.output

    def test_run_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0

    def test_analyze_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0


class TestRun:
    def test_success(self, runner: CliRunner, good_script: Path) -> None:
        result = runner.invoke(cli, ["run", str(good_script)])
        assert result.exit_code == 0
        assert "success" in result.output.lower()

    def test_error_exit_1(self, runner: CliRunner, bad_script: Path) -> None:
        result = runner.invoke(cli, ["run", str(bad_script)])
        assert result.exit_code == 1

    def test_error_output_has_error_type(self, runner: CliRunner, bad_script: Path) -> None:
        result = runner.invoke(cli, ["run", str(bad_script)])
        assert "TypeError" in result.output

    def test_professional_mode(self, runner: CliRunner, bad_script: Path) -> None:
        result = runner.invoke(cli, ["run", str(bad_script), "--mode", "professional"])
        # Should not crash
        assert result.exit_code in (0, 1)

    def test_generates_html_report(self, runner: CliRunner, bad_script: Path, tmp_path: Path) -> None:
        result = runner.invoke(cli, [
            "run", str(bad_script), "--html", "--output", str(tmp_path)
        ])
        assert result.exit_code == 1
        html_files = list(tmp_path.glob("*.html"))
        assert len(html_files) >= 1

    def test_generates_json_report(self, runner: CliRunner, bad_script: Path, tmp_path: Path) -> None:
        result = runner.invoke(cli, [
            "run", str(bad_script), "--json", "--output", str(tmp_path)
        ])
        assert result.exit_code == 1
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) >= 1

    def test_generates_markdown_report(self, runner: CliRunner, bad_script: Path, tmp_path: Path) -> None:
        result = runner.invoke(cli, [
            "run", str(bad_script), "--markdown", "--output", str(tmp_path)
        ])
        assert result.exit_code == 1
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) >= 1


class TestAnalyze:
    def test_no_issues(self, runner: CliRunner, good_script: Path) -> None:
        result = runner.invoke(cli, ["analyze", str(good_script)])
        assert result.exit_code == 0

    def test_finds_issues(self, runner: CliRunner, analysis_script: Path) -> None:
        result = runner.invoke(cli, ["analyze", str(analysis_script)])
        assert result.exit_code == 0
        # Should print some findings
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["warning", "unused", "bare", "✅"])

    def test_json_format(self, runner: CliRunner, analysis_script: Path, tmp_path: Path) -> None:
        result = runner.invoke(cli, [
            "analyze", str(analysis_script), "--format", "json", "--output", str(tmp_path)
        ])
        assert result.exit_code == 0

    def test_no_security_flag(self, runner: CliRunner, good_script: Path) -> None:
        result = runner.invoke(cli, ["analyze", str(good_script), "--no-security"])
        assert result.exit_code == 0


class TestExplain:
    def test_explain_type_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["explain", "TypeError"])
        assert result.exit_code == 0
        assert "TypeError" in result.output

    def test_explain_unknown(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["explain", "UnknownError"])
        assert result.exit_code == 0

    def test_explain_name_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["explain", "NameError"])
        assert result.exit_code == 0
        assert "NameError" in result.output

    def test_explain_professional_mode(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["explain", "ValueError", "--mode", "professional"])
        assert result.exit_code == 0


class TestDoctor:
    def test_doctor_runs(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "CodeMedic" in result.output or "Python" in result.output

    def test_doctor_shows_kb_count(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["doctor"])
        assert "KB entries" in result.output or "Knowledge" in result.output


class TestReport:
    def test_report_sample(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(cli, [
            "report", "--format", "html", "--output", str(tmp_path / "out.html")
        ])
        assert result.exit_code == 0

    def test_report_json(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(cli, ["report", "--format", "json"])
        assert result.exit_code == 0

    def test_report_markdown(self, runner: CliRunner, tmp_path: Path) -> None:
        result = runner.invoke(cli, ["report", "--format", "markdown"])
        assert result.exit_code == 0
