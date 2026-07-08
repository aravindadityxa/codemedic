# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] – 2026-07-08

### Added

**Core**
- `Runner` – executes Python scripts and callables, captures exception detail
- `TraceCollector`, `TraceResult`, `StackFrame` – structured traceback data
- `ExplanationEngine` – beginner and professional explanation modes
- `Fixer` – exception-specific patch generators with confidence scores
- `CodeAnalyzer` – AST-based static analysis with 14 check categories
- `SecurityChecker` – detects `eval`/`exec`, injection, pickle, weak hashes, hardcoded secrets
- `KnowledgeBase` – SQLite store with 40+ built-in exception entries
- `ReportGenerator` – HTML, JSON, and Markdown report generation
- `Formatter` – terminal UI with Rich formatting

**CLI**
- `codemedic run` – run script with error analysis and report generation
- `codemedic analyze` – static analysis with optional security scan
- `codemedic explain` – look up exception types
- `codemedic doctor` – environment diagnostics
- `codemedic report` – generate standalone report from previous result
- `codemedic version` – show installed version

**Knowledge Base**
- 40+ Python built-in exceptions with full coverage
- Description, causes, explanations, and analogies
- Before/after code examples and fix suggestions
- Difficulty ratings and category tags
- Official documentation links

**Package**
- PEP 561 `py.typed` marker for type checker support
- `pyproject.toml` with full metadata and dev extras
- GitHub Actions CI (Python 3.11, 3.12, 3.13)
- MIT License

**Testing**
- 228 pytest tests
- 91.85% line coverage

### Fixed
- Placeholder implementations replaced with working code
- Circular import removed between `__init__` and submodules
- `Formatter` dark/light theme logic corrected
- `_fix_key_error` no longer corrupts source lines
- `_get_docs_reference` reference error fixed
- `pyproject.toml` build backend corrected to `setuptools.build_meta`

---

## [0.1.0] – (pre-release, unpublished)

- Initial project scaffold with placeholder implementations
