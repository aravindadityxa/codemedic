"""Tests for codemedic.report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codemedic.config import Config
from codemedic.report import ReportGenerator

SAMPLE_DATA = {
    "error_type": "TypeError",
    "message": "can only concatenate str (not 'int') to str",
    "simple_explanation": "You tried to mix a string and an integer.",
    "analogy": "Like adding apples to invoices.",
    "how_to_avoid": "Use str() to convert the integer.",
    "root_cause": {
        "file": "example.py",
        "short_file": "example.py",
        "line": 3,
        "function": "<module>",
        "code": "print('Age: ' + 25)",
        "locals": {},
    },
    "fixes": [
        {
            "line_number": 3,
            "original_line": "print('Age: ' + 25)",
            "suggested_line": "print('Age: ' + str(25))",
            "description": "Convert int to str",
            "confidence": 0.9,
        }
    ],
    "analysis": [
        {"line": 1, "column": 0, "severity": "warning", "category": "test", "message": "Test issue"},
    ],
    "full_traceback": "Traceback (most recent call last):\n  File 'example.py', line 3\nTypeError: ...",
    "example_before": "print('Age: ' + 25)",
    "example_after": "print(f'Age: {25}')",
}


@pytest.fixture
def gen(tmp_path: Path) -> ReportGenerator:
    cfg = Config(output_folder=str(tmp_path))
    return ReportGenerator(cfg)


class TestHTMLReport:
    def test_creates_file(self, gen: ReportGenerator, tmp_path: Path) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_error_type(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        content = path.read_text(encoding="utf-8")
        assert "TypeError" in content

    def test_html_contains_explanation(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        content = path.read_text(encoding="utf-8")
        assert "mix a string" in content

    def test_html_contains_fix(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        content = path.read_text(encoding="utf-8")
        assert "Convert int to str" in content

    def test_html_contains_traceback(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        content = path.read_text(encoding="utf-8")
        assert "Traceback" in content

    def test_custom_filename(self, gen: ReportGenerator, tmp_path: Path) -> None:
        path = gen.generate(SAMPLE_DATA, format="html", filename="custom")
        assert path.name == "custom.html"

    def test_valid_html_structure(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="html")
        content = path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content


class TestJSONReport:
    def test_creates_file(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="json")
        assert path.exists()
        assert path.suffix == ".json"

    def test_valid_json(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_has_metadata(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "_meta" in data
        assert "codemedic_version" in data["_meta"]
        assert "python_version" in data["_meta"]

    def test_error_type_preserved(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["error_type"] == "TypeError"

    def test_custom_filename(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="json", filename="my_report")
        assert path.name == "my_report.json"


class TestMarkdownReport:
    def test_creates_file(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="markdown")
        assert path.exists()
        assert path.suffix == ".md"

    def test_md_alias(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="md")
        assert path.suffix == ".md"

    def test_contains_error_header(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="markdown")
        content = path.read_text(encoding="utf-8")
        assert "# " in content
        assert "TypeError" in content

    def test_contains_sections(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="markdown")
        content = path.read_text(encoding="utf-8")
        assert "What Happened" in content
        assert "Root Cause" in content
        assert "Suggested Fixes" in content

    def test_contains_traceback(self, gen: ReportGenerator) -> None:
        path = gen.generate(SAMPLE_DATA, format="markdown")
        content = path.read_text(encoding="utf-8")
        assert "Traceback" in content


class TestInvalidFormat:
    def test_raises_value_error(self, gen: ReportGenerator) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            gen.generate(SAMPLE_DATA, format="xlsx")


class TestOutputFolder:
    def test_creates_output_folder(self, tmp_path: Path) -> None:
        nested = tmp_path / "reports" / "subdir"
        cfg = Config(output_folder=str(nested))
        gen = ReportGenerator(cfg)
        gen.generate(SAMPLE_DATA, format="json")
        assert nested.exists()
