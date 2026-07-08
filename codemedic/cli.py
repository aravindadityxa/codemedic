"""Command-line interface for CodeMedic."""

from __future__ import annotations

import logging
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

import click

from . import __version__
from .analyzer import CodeAnalyzer
from .config import Config, load_config
from .formatter import Formatter
from .report import ReportGenerator
from .runner import Runner
from .utils import setup_logging

logger = logging.getLogger(__name__)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__, prog_name="CodeMedic", message="CodeMedic v%(version)s")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose/debug output.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """CodeMedic – Intelligent Python debugging assistant.

    \b
    Examples:
      codemedic run script.py
      codemedic analyze script.py
      codemedic explain TypeError
      codemedic doctor
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    level = logging.DEBUG if verbose else logging.WARNING
    setup_logging(level=level)


@cli.command()
@click.argument("filepath", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
@click.option("--mode", "-m", type=click.Choice(["beginner", "professional"]), default="beginner",
              show_default=True, help="Explanation verbosity mode.")
@click.option("--config", "-c", "config_path",
              type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
              default=None, help="Path to a codemedic.json config file.")
@click.option("--html/--no-html", default=False, help="Generate an HTML report.")
@click.option("--json/--no-json", "gen_json", default=False, help="Generate a JSON report.")
@click.option("--markdown/--no-markdown", default=False, help="Generate a Markdown report.")
@click.option("--output", "-o", default="./codemedic_reports",
              type=click.Path(file_okay=False, dir_okay=True),
              help="Output directory for reports.")
def run(
    filepath: Path,
    mode: str,
    config_path: Optional[Path],
    html: bool,
    gen_json: bool,
    markdown: bool,
    output: str,
) -> None:
    """Run a Python script with CodeMedic error handling.

    FILEPATH is the path to the Python script to execute.
    """
    cfg = load_config(config_path)
    cfg.mode = mode
    cfg.output_folder = output
    if html:
        cfg.generate_html = True
    if gen_json:
        cfg.generate_json = True
    if markdown:
        cfg.generate_markdown = True

    runner = Runner(mode=mode, config=cfg)
    formatter = Formatter(cfg)

    click.echo(f"Running {filepath}...")

    result = runner.run_file(filepath)

    # Always show static analysis warnings
    if result.analysis:
        warnings = [i for i in result.analysis if i.severity in ("warning", "error")]
        if warnings:
            formatter.print_analysis_report(
                [{"line": i.line, "column": i.column, "severity": i.severity,
                  "category": i.category, "message": i.message} for i in warnings]
            )

    if result.success:
        click.echo(click.style("OK  Script executed successfully.", fg="green"))
        if result.stdout:
            click.echo(result.stdout, nl=False)
    else:
        formatter.print_error_report(result.to_dict())

        if cfg.generate_html or cfg.generate_json or cfg.generate_markdown:
            report_gen = ReportGenerator(cfg)
            data = result.to_dict()
            if cfg.generate_html:
                p = report_gen.generate(data, format="html")
                click.echo(f"HTML report: {p}")
            if cfg.generate_json:
                p = report_gen.generate(data, format="json")
                click.echo(f"JSON report: {p}")
            if cfg.generate_markdown:
                p = report_gen.generate(data, format="markdown")
                click.echo(f"Markdown report: {p}")

        sys.exit(1)


@cli.command()
@click.argument("filepath", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path))
@click.option("--format", "-f", "fmt",
              type=click.Choice(["console", "html", "json", "markdown", "all"]),
              default="console", show_default=True, help="Output format.")
@click.option("--output", "-o", default="./codemedic_reports",
              type=click.Path(file_okay=False, dir_okay=True), help="Report output directory.")
@click.option("--security/--no-security", default=True,
              help="Include security checks (default: enabled).")
def analyze(filepath: Path, fmt: str, output: str, security: bool) -> None:
    """Analyse a Python file for static code issues.

    FILEPATH is the path to the Python script to analyse.
    """
    cfg = load_config()
    cfg.output_folder = output

    analyzer = CodeAnalyzer()
    formatter = Formatter(cfg)

    issues = analyzer.analyze_file(filepath)

    sec_warnings: list[Any] = []
    if security:
        from .security import check_file as sec_check
        sec_warnings = sec_check(filepath)

    if not issues and not sec_warnings:
        click.echo(click.style("No issues found.", fg="green"))
        return

    issue_dicts = [
        {"line": i.line, "column": i.column, "severity": i.severity,
         "category": i.category, "message": i.message}
        for i in issues
    ]

    if fmt in ("console", "all"):
        formatter.print_analysis_report(issue_dicts)
        if sec_warnings:
            formatter.print_security_report(sec_warnings)

    if fmt in ("html", "all"):
        data = {"file": str(filepath), "analysis": issue_dicts, "security": [
            {"line": w.line, "code": w.code, "severity": w.severity,
             "message": w.message, "recommendation": w.recommendation}
            for w in sec_warnings
        ]}
        p = ReportGenerator(cfg).generate(data, format="html", filename=f"analysis_{filepath.stem}")
        click.echo(f"HTML report: {p}")
    if fmt in ("json", "all"):
        data = {"file": str(filepath), "analysis": issue_dicts}
        p = ReportGenerator(cfg).generate(data, format="json", filename=f"analysis_{filepath.stem}")
        click.echo(f"JSON report: {p}")
    if fmt in ("markdown", "all"):
        data = {"file": str(filepath), "analysis": issue_dicts}
        p = ReportGenerator(cfg).generate(data, format="markdown", filename=f"analysis_{filepath.stem}")
        click.echo(f"Markdown report: {p}")


@cli.command()
@click.argument("exception_type")
@click.option("--mode", "-m", type=click.Choice(["beginner", "professional"]),
              default="beginner", show_default=True)
def explain(exception_type: str, mode: str) -> None:
    """Explain a Python exception type in plain English.

    EXCEPTION_TYPE is the name of the exception (e.g. TypeError, KeyError).
    """
    from .explanations import ExplanationEngine

    engine = ExplanationEngine(mode=mode)
    exp = engine.explain_by_name(exception_type)

    cfg = Config(mode=mode)
    formatter = Formatter(cfg)

    click.echo()
    formatter.print_error_report(exp)


@cli.command()
def doctor() -> None:
    """Run system diagnostics and report CodeMedic installation health."""
    from .database import KnowledgeBase

    cfg = load_config()
    formatter = Formatter(cfg)

    kb = KnowledgeBase()
    count = kb.count_errors()

    info = {
        "CodeMedic version": __version__,
        "Python version": sys.version.split()[0],
        "Python executable": sys.executable,
        "Platform": platform.platform(),
        "OS": f"{platform.system()} {platform.release()}",
        "Architecture": platform.machine(),
        "SQLite version": sqlite3.sqlite_version,
        "Knowledge base": str(kb.db_path),
        "KB entries": str(count),
        "Config mode": cfg.mode,
        "Dark mode": str(cfg.dark_mode),
        "Report folder": str(cfg.reports_path),
        "Rich": _check_package("rich"),
        "Click": _check_package("click"),
    }

    formatter.print_doctor_report(info)


@cli.command()
@click.option("--format", "-f", "fmt",
              type=click.Choice(["html", "json", "markdown"]),
              default="html", show_default=True, help="Report format.")
@click.option("--output", "-o", default=None,
              type=click.Path(dir_okay=False), help="Output file path.")
@click.option("--input", "-i", "input_json", default=None,
              type=click.Path(exists=True, dir_okay=False),
              help="JSON file produced by a previous 'codemedic run --json' run.")
def report(fmt: str, output: Optional[str], input_json: Optional[str]) -> None:
    """Generate a standalone report from a previous JSON run result.

    Use --input to specify a JSON file from a prior run.
    Without --input a sample report is generated.
    """
    import json as _json

    cfg = load_config()
    if output:
        cfg.output_folder = str(Path(output).parent)
    gen = ReportGenerator(cfg)

    if input_json:
        with open(input_json, encoding="utf-8") as fh:
            data = _json.load(fh)
        out_name = Path(input_json).stem
    else:
        # Demo data
        data = {
            "error_type": "TypeError",
            "message": "can only concatenate str (not 'int') to str",
            "simple_explanation": "You tried to add a string to an integer. Python needs them to be the same type.",
            "analogy": "Like trying to add apples and invoices – they're different things.",
            "how_to_avoid": "Use str() to convert the integer first, or use an f-string.",
            "root_cause": {"file": "example.py", "short_file": "example.py", "line": 3,
                           "function": "<module>", "code": "print('Age: ' + 25)"},
            "fixes": [{"line_number": 3, "original_line": "print('Age: ' + 25)",
                       "suggested_line": "print('Age: ' + str(25))", "description": "Convert int to str.", "confidence": 0.9}],
            "full_traceback": "Traceback (most recent call last):\n  File 'example.py', line 3\nTypeError: ...",
            "example_before": "print('Age: ' + 25)",
            "example_after": "print(f'Age: {25}')",
        }
        out_name = output or f"sample_report"

    out_path = gen.generate(data, format=fmt, filename=str(Path(out_name).name) if output else None)
    click.echo(f"Report generated: {out_path}")


@cli.command(name="version")
def version_cmd() -> None:
    """Show the installed CodeMedic version."""
    click.echo(f"CodeMedic v{__version__}")


def _check_package(name: str) -> str:
    try:
        import importlib.metadata
        v = importlib.metadata.version(name)
        return f"installed ({v})"
    except Exception:
        return "not found"
