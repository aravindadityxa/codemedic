"""Tests for codemedic.config."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codemedic.config import DEFAULT_CONFIG, Config, load_config


class TestConfig:
    def test_defaults(self) -> None:
        cfg = Config()
        assert cfg.mode == "beginner"
        assert cfg.dark_mode is True
        assert cfg.verbosity == 1
        assert cfg.generate_html is True

    def test_from_dict_partial(self) -> None:
        cfg = Config.from_dict({"mode": "professional"})
        assert cfg.mode == "professional"
        assert cfg.dark_mode is True  # default preserved

    def test_from_dict_unknown_keys_ignored(self) -> None:
        cfg = Config.from_dict({"mode": "beginner", "nonexistent_key": True})
        assert cfg.mode == "beginner"

    def test_to_dict(self) -> None:
        cfg = Config(mode="professional", verbosity=3)
        d = cfg.to_dict()
        assert d["mode"] == "professional"
        assert d["verbosity"] == 3

    def test_round_trip(self) -> None:
        cfg = Config(mode="professional", dark_mode=False, verbosity=2)
        d = cfg.to_dict()
        cfg2 = Config.from_dict(d)
        assert cfg.mode == cfg2.mode
        assert cfg.dark_mode == cfg2.dark_mode

    def test_db_path_is_path(self) -> None:
        cfg = Config()
        assert isinstance(cfg.db_path, Path)

    def test_reports_path_is_path(self) -> None:
        cfg = Config()
        assert isinstance(cfg.reports_path, Path)

    def test_numeric_log_level_warning(self) -> None:
        import logging

        cfg = Config(log_level="WARNING")
        assert cfg.numeric_log_level == logging.WARNING

    def test_numeric_log_level_debug(self) -> None:
        import logging

        cfg = Config(log_level="DEBUG")
        assert cfg.numeric_log_level == logging.DEBUG

    def test_numeric_log_level_invalid(self) -> None:
        import logging

        cfg = Config(log_level="INVALID")
        # falls back to WARNING
        assert cfg.numeric_log_level == logging.WARNING


class TestLoadConfig:
    def test_returns_config(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, Config)

    def test_load_from_file(self, tmp_path: Path) -> None:
        cfg_file = tmp_path / "codemedic.json"
        cfg_file.write_text(json.dumps({"mode": "professional", "verbosity": 3}))
        cfg = load_config(cfg_file)
        assert cfg.mode == "professional"
        assert cfg.verbosity == 3

    def test_invalid_json_falls_back(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        cfg = load_config(bad_file)
        # Should fall back to defaults
        assert cfg.mode == "beginner"

    def test_nonexistent_path_uses_defaults(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path / "nonexistent.json")
        assert cfg.mode == DEFAULT_CONFIG["mode"]
