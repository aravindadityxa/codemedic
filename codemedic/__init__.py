"""CodeMedic – Intelligent Python Debugging Library.

Provides runtime error analysis, human-friendly explanations, root-cause
identification, and actionable fix suggestions.

Quick start::

    from codemedic import Runner

    runner = Runner(mode="beginner")
    result = runner.run_file("my_script.py")

    if not result.success:
        print(result.explanation["simple_explanation"])
        for fix in result.fixes:
            print(fix.description)

CLI::

    codemedic run script.py
    codemedic analyze script.py
    codemedic explain TypeError
    codemedic doctor
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Aravind Adityaa M"
__license__ = "MIT"

from .analyzer import AnalysisIssue, CodeAnalyzer
from .cli import cli
from .config import Config, load_config
from .database import KnowledgeBase
from .explanations import ExplanationEngine
from .fixer import Fixer, PatchSuggestion
from .formatter import Formatter
from .report import ReportGenerator
from .runner import RunResult, Runner
from .security import SecurityChecker, SecurityWarning, check_file, check_source
from .trace import StackFrame, TraceCollector, TraceResult
from .utils import get_version, indent, setup_logging

__all__ = [
    "Runner",
    "RunResult",
    "TraceCollector",
    "TraceResult",
    "StackFrame",
    "CodeAnalyzer",
    "AnalysisIssue",
    "ExplanationEngine",
    "Fixer",
    "PatchSuggestion",
    "ReportGenerator",
    "Formatter",
    "KnowledgeBase",
    "SecurityChecker",
    "SecurityWarning",
    "check_file",
    "check_source",
    "Config",
    "load_config",
    "get_version",
    "setup_logging",
    "indent",
    "cli",
    "__version__",
    "__author__",
    "__license__",
]
