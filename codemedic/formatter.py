"""Rich terminal formatter for CodeMedic output."""

from __future__ import annotations

import logging
from typing import Any, Optional

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.theme import Theme

from .config import Config
from .fixer import PatchSuggestion

logger = logging.getLogger(__name__)

_DARK_THEME = Theme({
    "error.title": "bold red",
    "error.border": "red",
    "info.border": "bright_blue",
    "warn.border": "yellow",
    "fix.border": "green",
    "trace.border": "dim white",
    "success": "bold green",
    "dim_text": "dim white",
    "severity.error": "bold red",
    "severity.warning": "bold yellow",
    "severity.info": "cyan",
})

_LIGHT_THEME = Theme({
    "error.title": "bold red",
    "error.border": "red",
    "info.border": "blue",
    "warn.border": "dark_orange",
    "fix.border": "dark_green",
    "trace.border": "grey50",
    "success": "bold dark_green",
    "dim_text": "grey50",
    "severity.error": "bold red",
    "severity.warning": "bold dark_orange",
    "severity.info": "blue",
})


class Formatter:
    """Renders CodeMedic output to the terminal using Rich.

    Args:
        config: Optional :class:`~codemedic.config.Config` instance.
        console: Optional pre-built :class:`rich.console.Console` (useful for testing).
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.config: Config = config or Config()
        theme = _DARK_THEME if self.config.dark_mode else _LIGHT_THEME
        self.console: Console = console or Console(theme=theme)

    def print_error_report(self, data: dict[str, Any]) -> None:
        """Print a full error report to the terminal."""
        self.console.print()

        error_type = data.get("error_type", "Error")
        message = escape(str(data.get("message", "")))
        self.console.print(Panel(
            f"[error.title]🚨  {error_type}[/error.title]\n[dim]{message}[/dim]",
            border_style="error.border",
            title="[bold] CodeMedic [/bold]",
            title_align="center",
            expand=False,
        ))

        simple = data.get("simple_explanation", "")
        if simple:
            self.console.print(Panel(
                escape(simple),
                title="[bold]📖  What happened?[/bold]",
                border_style="info.border",
                expand=False,
            ))

        analogy = data.get("analogy", "")
        if analogy and analogy != "No analogy available for this exception type.":
            self.console.print(f"  [dim_text]💡 Analogy: {escape(analogy)}[/dim_text]")

        root: dict[str, Any] = data.get("root_cause", {})
        if root:
            code_line = escape(str(root.get("code", "")))
            locals_str = ""
            if root.get("locals"):
                locs = root["locals"]
                visible = dict(list(locs.items())[:6])
                locals_str = "\n".join(f"  [dim_text]{k}[/dim_text] = {escape(str(v))}" for k, v in visible.items())
                if len(locs) > 6:
                    locals_str += f"\n  [dim_text]… {len(locs) - 6} more[/dim_text]"

            body = (
                f"[bold]File:[/bold]     {escape(str(root.get('short_file', root.get('file', 'unknown'))))}\n"
                f"[bold]Line:[/bold]     {root.get('line', '?')}\n"
                f"[bold]Function:[/bold] {escape(str(root.get('function', '?')))}\n"
                f"[bold]Code:[/bold]     [code]{code_line}[/code]"
            )
            if locals_str:
                body += f"\n[bold]Locals:[/bold]\n{locals_str}"

            self.console.print(Panel(
                body,
                title="[bold]🔍  Root Cause[/bold]",
                border_style="warn.border",
                expand=False,
            ))

        how_to = data.get("how_to_avoid", "")
        if how_to:
            self.console.print(Panel(
                escape(how_to),
                title="[bold]📚  How to avoid[/bold]",
                border_style="info.border",
                expand=False,
            ))

        fixes: list[Any] = data.get("fixes", [])
        if fixes:
            self._print_fixes(fixes)

        before = data.get("example_before", "")
        after = data.get("example_after", "")
        if before and after:
            self._print_examples(before, after)

        if self.config.mode == "professional":
            tb = data.get("full_traceback", "")
            if tb:
                self.console.print(Panel(
                    Syntax(tb, "python-traceback", theme="monokai", line_numbers=False),
                    title="[bold]📄  Full Traceback[/bold]",
                    border_style="trace.border",
                    expand=False,
                ))
            docs = data.get("docs_reference", "")
            if docs:
                self.console.print(f"  [dim_text]📎 Docs: {escape(docs)}[/dim_text]")

        self.console.print()

    def print_analysis_report(self, issues: list[dict[str, Any]]) -> None:
        """Print a static analysis report to the terminal."""
        if not issues:
            self.console.print("[success]✅  No issues found![/success]")
            return

        table = Table(
            title="📊  Static Analysis Report",
            show_header=True,
            header_style="bold",
            border_style="dim",
        )
        table.add_column("Line", style="cyan", justify="right", width=6)
        table.add_column("Severity", width=9)
        table.add_column("Category", style="yellow", width=22)
        table.add_column("Message")

        severity_styles = {
            "error": "[severity.error]",
            "warning": "[severity.warning]",
            "info": "[severity.info]",
        }
        severity_icons = {"error": "✖", "warning": "⚠", "info": "ℹ"}

        for issue in sorted(issues, key=lambda x: (x.get("line", 0), x.get("severity", ""))):
            sev = issue.get("severity", "info")
            style = severity_styles.get(sev, "")
            icon = severity_icons.get(sev, "•")
            table.add_row(
                str(issue.get("line", 0)),
                f"{style}{icon} {sev.upper()}[/]",
                issue.get("category", ""),
                escape(issue.get("message", "")),
            )

        self.console.print(table)

    def print_security_report(self, warnings: list[Any]) -> None:
        """Print security warnings to the terminal."""
        if not warnings:
            self.console.print("[success]🔒  No security issues found.[/success]")
            return

        table = Table(
            title="🔒  Security Warnings",
            show_header=True,
            header_style="bold red",
            border_style="red",
        )
        table.add_column("Line", style="cyan", justify="right", width=6)
        table.add_column("Code", width=8)
        table.add_column("Severity", width=8)
        table.add_column("Message")
        table.add_column("Recommendation")

        for w in warnings:
            severity_color = {"high": "red", "medium": "yellow", "low": "blue"}.get(w.severity, "white")
            table.add_row(
                str(w.line),
                w.code,
                f"[{severity_color}]{w.severity.upper()}[/{severity_color}]",
                escape(w.message),
                escape(w.recommendation),
            )

        self.console.print(table)

    def print_doctor_report(self, info: dict[str, Any]) -> None:
        """Print the `codemedic doctor` diagnostics panel."""
        self.console.print(Panel(
            "\n".join(f"[bold]{k}:[/bold] {escape(str(v))}" for k, v in info.items()),
            title="[bold]🔬  CodeMedic Doctor[/bold]",
            border_style="info.border",
            expand=False,
        ))

    def _print_fixes(self, fixes: list[Any]) -> None:
        """Render the fixes table."""
        table = Table(
            title="🛠️  Suggested Fixes",
            show_header=True,
            header_style="bold green",
            border_style="fix.border",
        )
        table.add_column("Line", style="cyan", justify="right", width=6)
        table.add_column("Confidence", width=10)
        table.add_column("Description")
        table.add_column("Suggested Change")

        for fix in fixes:
            if isinstance(fix, PatchSuggestion):
                lineno = fix.line_number
                conf = fix.confidence
                desc = fix.description
                suggested = fix.suggested_line
            else:
                lineno = fix.get("line_number", 0)
                conf = fix.get("confidence", 0.0)
                desc = fix.get("description", "")
                suggested = fix.get("suggested_line", "")

            conf_color = "green" if conf >= 0.75 else ("yellow" if conf >= 0.5 else "red")
            table.add_row(
                str(lineno),
                f"[{conf_color}]{conf:.0%}[/{conf_color}]",
                escape(desc[:100]),
                escape(str(suggested)[:80]) if suggested else "[dim]N/A[/dim]",
            )

        self.console.print(table)

    def _print_examples(self, before: str, after: str) -> None:
        """Render before/after code examples side by side."""
        self.console.print(Panel(
            Syntax(before.strip(), "python", theme="monokai"),
            title="[bold red]❌  Before[/bold red]",
            border_style="red",
            expand=False,
        ))
        self.console.print(Panel(
            Syntax(after.strip(), "python", theme="monokai"),
            title="[bold green]✅  After[/bold green]",
            border_style="green",
            expand=False,
        ))
