"""Allow running the package as a module: ``python -m codemedic``."""

from __future__ import annotations

import sys


def _ensure_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 on platforms where the default
    encoding is not UTF-8 (e.g. Windows with CP1252 console).

    Uses ``reconfigure()`` when available (Python 3.7+, TextIOWrapper streams)
    and falls back silently — the CLI still works, just without emoji.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_ensure_utf8_stdout()

from .cli import cli  # noqa: E402 — must come after stdout reconfiguration

if __name__ == "__main__":
    cli()
