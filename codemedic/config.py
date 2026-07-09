"""Configuration management for CodeMedic."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "mode": "beginner",
    "dark_mode": True,
    "verbosity": 1,
    "output_folder": "./codemedic_reports",
    "generate_html": True,
    "generate_json": True,
    "generate_markdown": False,
    "knowledge_base": "~/.codemedic/errors.db",
    "log_file": None,
    "log_level": "WARNING",
}


@dataclass
class Config:
    """Application-wide configuration.

    Attributes:
        mode: Explanation style – ``"beginner"`` or ``"professional"``.
        dark_mode: Enable dark terminal theme.
        verbosity: Output verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug).
        output_folder: Directory for generated reports.
        generate_html: Auto-generate HTML report on error.
        generate_json: Auto-generate JSON report on error.
        generate_markdown: Auto-generate Markdown report on error.
        knowledge_base: Path to the SQLite knowledge-base file.
        log_file: Optional path for the log file.
        log_level: String log level (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).
    """

    mode: str = "beginner"
    dark_mode: bool = True
    verbosity: int = 1
    output_folder: str = "./codemedic_reports"
    generate_html: bool = True
    generate_json: bool = True
    generate_markdown: bool = False
    knowledge_base: str = "~/.codemedic/errors.db"
    log_file: Optional[str] = None
    log_level: str = "WARNING"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config from a plain dictionary, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**{**DEFAULT_CONFIG, **filtered})

    def to_dict(self) -> dict[str, Any]:
        """Serialise the config to a plain dictionary."""
        return {
            "mode": self.mode,
            "dark_mode": self.dark_mode,
            "verbosity": self.verbosity,
            "output_folder": self.output_folder,
            "generate_html": self.generate_html,
            "generate_json": self.generate_json,
            "generate_markdown": self.generate_markdown,
            "knowledge_base": self.knowledge_base,
            "log_file": self.log_file,
            "log_level": self.log_level,
        }

    @property
    def numeric_log_level(self) -> int:
        """Return the numeric logging level for :attr:`log_level`."""
        level = logging.getLevelName(self.log_level.upper())
        return level if isinstance(level, int) else logging.WARNING

    @property
    def db_path(self) -> Path:
        """Resolved path to the SQLite knowledge-base file."""
        return Path(self.knowledge_base).expanduser().resolve()

    @property
    def reports_path(self) -> Path:
        """Resolved path to the report output folder."""
        return Path(self.output_folder).expanduser().resolve()


def load_config(path: Optional[Path] = None) -> Config:
    """Load configuration from a JSON file, falling back to defaults.

    Searches in order: ``./codemedic.json``, ``~/.codemedic/config.json``,
    ``~/.codemedic.json``. Returns default Config if no file is found.

    Args:
        path: Explicit path to a JSON config file.
    """
    if path is None:
        candidates: list[Path] = [
            Path.cwd() / "codemedic.json",
            Path.home() / ".codemedic" / "config.json",
            Path.home() / ".codemedic.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break

    if path and path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                data: dict[str, Any] = json.load(fh)
            logger.debug("Loaded config from %s", path)
            return Config.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read config file %s: %s – using defaults.", path, exc)

    return Config()
