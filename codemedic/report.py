"""Report generation – HTML, JSON, Markdown, and console summary."""

from __future__ import annotations

import json
import logging
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import Config
from .utils import get_version

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reports in multiple formats from CodeMedic run data.

    Args:
        config: Optional :class:`~codemedic.config.Config` instance.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config: Config = config or Config()
        self.output_folder: Path = self.config.reports_path
        self.output_folder.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        data: dict[str, Any],
        format: str = "html",
        filename: Optional[str] = None,
    ) -> Path:
        """Generate a report file.

        Args:
            data: Error/analysis data dictionary (as from
                  :meth:`~codemedic.runner.RunResult.to_dict`).
            format: ``"html"``, ``"json"``, or ``"markdown"``/``"md"``.
            filename: Base name without extension (auto-generated if *None*).

        Returns:
            :class:`~pathlib.Path` to the generated file.

        Raises:
            ValueError: For unsupported *format* values.
        """
        fmt = format.lower()
        if fmt == "html":
            return self._generate_html(data, filename)
        if fmt == "json":
            return self._generate_json(data, filename)
        if fmt in ("markdown", "md"):
            return self._generate_markdown(data, filename)
        raise ValueError(
            f"Unsupported report format: '{format}'. Use html, json, or markdown."
        )

    def _generate_html(self, data: dict[str, Any], filename: Optional[str]) -> Path:
        base = filename or f"report_{self._ts()}"
        if not base.endswith(".html"):
            base += ".html"
        path = self.output_folder / base
        path.write_text(self._render_html(data), encoding="utf-8")
        logger.info("HTML report written to %s", path)
        return path

    def _render_html(self, data: dict[str, Any]) -> str:  # noqa: PLR0912
        error_type = data.get("error_type", "Unknown")
        message = self._esc(str(data.get("message", "")))
        simple = self._esc(str(data.get("simple_explanation", "")))
        analogy = self._esc(str(data.get("analogy", "")))
        how_to = self._esc(str(data.get("how_to_avoid", "")))
        root: dict[str, Any] = data.get("root_cause", {})
        fixes: list[Any] = data.get("fixes", [])
        tb = self._esc(str(data.get("full_traceback", "")))
        analysis: list[Any] = data.get("analysis", [])
        before = self._esc(str(data.get("example_before", "")))
        after = self._esc(str(data.get("example_after", "")))

        fixes_html = ""
        if fixes:
            rows = ""
            for f in fixes:
                if isinstance(f, dict):
                    ln = f.get("line_number", "")
                    desc = self._esc(str(f.get("description", "")))
                    sug = self._esc(str(f.get("suggested_line", "")))
                    conf = f"{float(f.get('confidence', 0)):.0%}"
                else:
                    ln = getattr(f, "line_number", "")
                    desc = self._esc(str(getattr(f, "description", "")))
                    sug = self._esc(str(getattr(f, "suggested_line", "")))
                    conf = f"{getattr(f, 'confidence', 0):.0%}"
                rows += (
                    f"<tr><td>{ln}</td><td>{desc}</td>"
                    f"<td><code>{sug}</code></td><td>{conf}</td></tr>"
                )
            fixes_html = (
                "<table>\n"
                "  <thead><tr><th>Line</th><th>Description</th>"
                "<th>Suggested</th><th>Confidence</th></tr></thead>\n"
                f"  <tbody>{rows}</tbody>\n"
                "</table>"
            )
        else:
            fixes_html = "<p><em>No specific fix suggestions generated.</em></p>"

        analysis_html = ""
        if analysis:
            rows = ""
            for i in analysis:
                if isinstance(i, dict):
                    line_num = i.get('line', '')
                    severity = i.get('severity', 'info')
                    category = self._esc(str(i.get('category', '')))
                    message = self._esc(str(i.get('message', '')))
                    rows += (f"<tr><td>{line_num}</td>"
                             f"<td class='sev-{severity}'>{severity.upper()}</td>"
                             f"<td>{category}</td>"
                             f"<td>{message}</td></tr>")
            analysis_html = (
                "<table>\n"
                "  <thead><tr><th>Line</th><th>Severity</th>"
                "<th>Category</th><th>Message</th></tr></thead>\n"
                f"  <tbody>{rows}</tbody>\n"
                "</table>"
            )

        examples_html = ""
        if before and after:
            examples_html = (
                '<div class="examples">\n'
                '  <div class="example before">'
                "<h3>❌ Before</h3>"
                f"<pre><code>{before}</code></pre></div>\n"
                '  <div class="example after">'
                "<h3>✅ After</h3>"
                f"<pre><code>{after}</code></pre></div>\n"
                "</div>"
            )

        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="UTF-8">\n'
            '  <meta name="viewport" '
            'content="width=device-width, initial-scale=1.0">\n'
            f"  <title>CodeMedic Report – {error_type}</title>\n"
            "  <style>\n"
            "    *, *::before, *::after "
            "{ box-sizing: border-box; margin: 0; padding: 0; }\n"
            "    body { font-family: -apple-system, BlinkMacSystemFont, "
            "'Segoe UI', Roboto, sans-serif;\n"
            "            background: #0f1117; color: #e0e0e0; padding: 2rem; "
            "line-height: 1.6; }\n"
            "    .container { max-width: 900px; margin: 0 auto; }\n"
            "    h1 { color: #ff6b6b; font-size: 1.8rem; "
            "margin-bottom: 0.25rem; }\n"
            "    h2 { color: #7bc8f6; margin: 1.5rem 0 0.5rem; "
            "font-size: 1.1rem; border-bottom: 1px solid #333; "
            "padding-bottom: 4px; }\n"
            "    h3 { color: #c3c3c3; font-size: 1rem; "
            "margin-bottom: 0.4rem; }\n"
            "    .card { background: #1a1d27; border-radius: 8px; "
            "padding: 1.2rem 1.5rem; margin: 1rem 0; "
            "border-left: 4px solid #444; }\n"
            "    .card.error { border-color: #ff6b6b; }\n"
            "    .card.info  { border-color: #7bc8f6; }\n"
            "    .card.warn  { border-color: #ffd93d; }\n"
            "    .card.fix   { border-color: #6bcb77; }\n"
            "    .badge { display:inline-block; padding:2px 8px; "
            "border-radius:4px; font-size:0.75rem; font-weight:600; }\n"
            "    table { width: 100%; border-collapse: collapse; "
            "margin-top: 0.5rem; font-size: 0.9rem; }\n"
            "    th, td { padding: 0.5rem 0.75rem; text-align: left; "
            "border-bottom: 1px solid #2a2d3a; }\n"
            "    th { background: #1f2235; color: #7bc8f6; }\n"
            "    pre, code { font-family: 'JetBrains Mono', Consolas, "
            "monospace; font-size: 0.85rem;\n"
            "                 background: #11131d; padding: 0.2em 0.4em; "
            "border-radius: 3px; }\n"
            "    pre { padding: 1rem; overflow-x: auto; "
            "border-radius: 6px; }\n"
            "    .examples { display: grid; "
            "grid-template-columns: 1fr 1fr; gap: 1rem; "
            "margin-top: 0.5rem; }\n"
            "    .example.before pre { border-left: 4px solid #ff6b6b; }\n"
            "    .example.after  pre { border-left: 4px solid #6bcb77; }\n"
            "    .meta { color: #666; font-size: 0.8rem; margin-top: 2rem; "
            "border-top: 1px solid #222; padding-top: 1rem; }\n"
            "    .sev-error   { color: #ff6b6b; font-weight: 600; }\n"
            "    .sev-warning { color: #ffd93d; font-weight: 600; }\n"
            "    .sev-info    { color: #7bc8f6; }\n"
            "  </style>\n"
            "</head>\n"
            "<body>\n"
            "<div class=\"container\">\n"
            f"  <h1>🚨 {error_type}</h1>\n"
            f'  <p style="color:#aaa">{message}</p>\n'
            "\n"
            '  <div class="card error">\n'
            "    <h2>📖 What Happened</h2>\n"
            f"    <p>{simple}</p>\n"
            "    "
            + (
                f'<p style="color:#aaa;font-style:italic;'
                f'margin-top:0.5rem">💡 {analogy}</p>'
                if analogy
                else ""
            )
            + "\n"
            "  </div>\n"
            "\n"
            '  <div class="card warn">\n'
            "    <h2>🔍 Root Cause</h2>\n"
            f"    <p><strong>File:</strong> "
            f"{self._esc(str(root.get('file','N/A')))}</p>\n"
            f"    <p><strong>Line:</strong> {root.get('line','N/A')}</p>\n"
            f"    <p><strong>Function:</strong> "
            f"{self._esc(str(root.get('function','N/A')))}</p>\n"
            f"    <p><strong>Code:</strong> <code>"
            f"{self._esc(str(root.get('code','')))}</code></p>\n"
            "  </div>\n"
            "\n"
            '  <div class="card info">\n'
            "    <h2>📚 How to Avoid</h2>\n"
            f"    <p>{how_to}</p>\n"
            "  </div>\n"
            "\n"
            '  <div class="card fix">\n'
            "    <h2>🛠️ Suggested Fixes</h2>\n"
            f"    {fixes_html}\n"
            "  </div>\n"
            "\n"
            + (
                f'  <div class="card info"><h2>💡 Code Examples</h2>'
                f"{examples_html}</div>\n"
                if examples_html
                else ""
            )
            + (
                f'  <div class="card"><h2>📊 Static Analysis '
                f"({len(analysis)} issues)</h2>"
                f"{analysis_html}</div>\n"
                if analysis_html
                else ""
            )
            + (
                f'  <div class="card"><h2>📄 Full Traceback</h2>'
                f"<pre>{tb}</pre></div>\n"
                if tb
                else ""
            )
            + '  <div class="meta">\n'
            + "    <p>Generated by <strong>CodeMedic v"
            + f"{get_version()}</strong> on "
            + f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n"
            + f"    <p>Python {sys.version} | "
            + f"{platform.system()} {platform.release()} | "
            + f"{platform.machine()}</p>\n"
            "  </div>\n"
            "</div>\n"
            "</body>\n"
            "</html>"
        )

    def _generate_json(self, data: dict[str, Any], filename: Optional[str]) -> Path:
        base = filename or f"report_{self._ts()}"
        if not base.endswith(".json"):
            base += ".json"
        path = self.output_folder / base

        serialisable = self._make_serialisable(data)
        serialisable["_meta"] = {
            "generated_at": datetime.now().isoformat(),
            "codemedic_version": get_version(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "os": platform.system(),
            "arch": platform.machine(),
        }

        with path.open("w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, indent=2, default=str)
        logger.info("JSON report written to %s", path)
        return path

    def _generate_markdown(self, data: dict[str, Any], filename: Optional[str]) -> Path:
        base = filename or f"report_{self._ts()}"
        if not base.endswith(".md"):
            base += ".md"
        path = self.output_folder / base
        path.write_text(self._render_markdown(data), encoding="utf-8")
        logger.info("Markdown report written to %s", path)
        return path

    def _render_markdown(self, data: dict[str, Any]) -> str:
        error_type = data.get("error_type", "Unknown")
        message = data.get("message", "")
        simple = data.get("simple_explanation", "")
        analogy = data.get("analogy", "")
        how_to = data.get("how_to_avoid", "")
        root = data.get("root_cause", {})
        fixes = data.get("fixes", [])
        tb = data.get("full_traceback", "")
        analysis = data.get("analysis", [])

        lines: list[str] = [
            f"# 🚨 CodeMedic Report – {error_type}",
            "",
            f"> **{error_type}**: {message}",
            "",
            "---",
            "",
            "## 📖 What Happened",
            "",
            simple,
            "",
        ]

        if analogy:
            lines += [f"_💡 Analogy: {analogy}_", ""]

        if root:
            lines += [
                "## 🔍 Root Cause",
                "",
                f"| Field    | Value |",
                f"|----------|-------|",
                f"| File     | `{root.get('file', 'N/A')}` |",
                f"| Line     | {root.get('line', 'N/A')} |",
                f"| Function | `{root.get('function', 'N/A')}` |",
                f"| Code     | `{root.get('code', '')}` |",
                "",
            ]

        if how_to:
            lines += ["## 📚 How to Avoid", "", how_to, ""]

        if fixes:
            lines += ["## 🛠️ Suggested Fixes", ""]
            for f in fixes:
                if isinstance(f, dict):
                    ln, desc, sug, conf = (
                        f.get("line_number", ""), f.get("description", ""),
                        f.get("suggested_line", ""), float(f.get("confidence", 0)),
                    )
                else:
                    ln, desc, sug, conf = (
                        getattr(f, "line_number", ""), getattr(f, "description", ""),
                        getattr(f, "suggested_line", ""), getattr(f, "confidence", 0),
                    )
                lines += [
                    f"### Fix at line {ln} (confidence: {conf:.0%})",
                    "",
                    desc,
                    "",
                    f"```python",
                    str(sug),
                    "```",
                    "",
                ]

        if analysis:
            lines += ["## 📊 Static Analysis", ""]
            header = "| Line | Severity | Category | Message |"
            sep = "|------|----------|----------|---------|"
            lines += [header, sep]
            for i in analysis:
                if isinstance(i, dict):
                    line_num = i.get('line', '')
                    severity = i.get('severity', '').upper()
                    category = i.get('category', '')
                    message = i.get('message', '')
                    lines.append(
                        f"| {line_num} | {severity} | {category} | {message} |"
                    )
            lines.append("")

        if tb:
            lines += ["## 📄 Full Traceback", "", "```", tb, "```", ""]

        lines += [
            "---",
            "",
            f"_Generated by **CodeMedic v{get_version()}** on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_  ",
            f"_Python {sys.version.split()[0]} | "
            f"{platform.system()} {platform.release()}_",
        ]

        return "\n".join(lines)

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _esc(s: str) -> str:
        """Escape HTML special characters."""
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
        )

    def _make_serialisable(self, obj: Any) -> Any:
        """Recursively convert objects to JSON-serialisable form."""
        if isinstance(obj, dict):
            return {k: self._make_serialisable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serialisable(i) for i in obj]
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return obj
