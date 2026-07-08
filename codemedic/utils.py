"""Utility functions for CodeMedic."""

from __future__ import annotations

import importlib.metadata
import logging
import sys
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Return the installed package version, falling back to the inline constant."""
    try:
        return importlib.metadata.version("codemedic")
    except importlib.metadata.PackageNotFoundError:
        # When running from source without installation
        from codemedic import __version__

        return __version__


def setup_logging(
    level: int = logging.WARNING,
    log_file: Optional[Union[str, Path]] = None,
    *,
    force: bool = False,
) -> None:
    """Configure root logging for the application.

    Args:
        level: Logging level (e.g. ``logging.INFO``).
        log_file: Optional path to a log file. When *None* only stdout is used.
        force: If *True*, reconfigure even if handlers are already present.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=force,
    )
    logger.debug("Logging initialised at level %s", logging.getLevelName(level))


def truncate_string(s: str, max_len: int = 200) -> str:
    """Return *s* truncated to *max_len* characters with an ellipsis indicator.

    Args:
        s: Input string.
        max_len: Maximum allowed length (default 200).

    Returns:
        Truncated string.
    """
    if len(s) <= max_len:
        return s
    return s[:max_len] + "… (truncated)"


def safe_repr(obj: object, max_len: int = 200) -> str:
    """Return a safe string representation of *obj*, never raising.

    Args:
        obj: Any Python object.
        max_len: Maximum length of the representation.

    Returns:
        String representation or ``'<unrepresentable>'``.
    """
    try:
        r = repr(obj)
        return truncate_string(r, max_len)
    except Exception:  # noqa: BLE001
        return "<unrepresentable>"


def indent(text: str, spaces: int = 4) -> str:
    """Indent every line of *text* by *spaces* spaces.

    Args:
        text: Multi-line string.
        spaces: Number of spaces to prepend.

    Returns:
        Indented string.
    """
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.splitlines())
