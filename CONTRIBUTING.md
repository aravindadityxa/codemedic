# Contributing to CodeMedic

We welcome contributions. Here's how to get started.

## Setup

Clone the repository and install in development mode:

```bash
git clone https://github.com/aravindadityxa/codemedic
cd codemedic
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Testing

Run the full test suite:

```bash
pytest tests/ -v --cov=codemedic --cov-report=term-missing
```

Maintain 80% coverage (currently ~92%).

## Code Style

Follow these standards:

- **Format** with `black` (line length 100)
- **Sort imports** with `isort`
- **Lint** with `flake8`
- **Type check** with `mypy`
- All public functions and classes must have docstrings and type hints

Quick commands:

```bash
black codemedic/ tests/
isort codemedic/ tests/
flake8 codemedic/
mypy codemedic/
```

## Adding Exception Entries

Edit `codemedic/database.py` and add to `_DEFAULT_ERRORS`:

```python
(
    "MyException",
    "Short description.",
    "Why it happens.",
    "Common causes.",
    "Simple explanation.",
    "Real-world analogy.",
    "How to fix it.",
    "broken_code()",
    "fixed_code()",
    1,                           # difficulty: 1-3
    "category",
    "https://docs.python.org/",
),
```

Add tests in `tests/test_database.py` and `tests/test_explanations.py`.

## Adding Fix Handlers

In `codemedic/fixer.py`, add a method:

```python
def _fix_myexception(self, trace: TraceResult) -> list[PatchSuggestion]:
    # implementation
    pass
```

Register it in the `suggest_fixes()` method and add tests in `tests/test_fixer.py`.

## Adding Analysis Checks

In `codemedic/analyzer.py`, add a visitor method to `_AnalyzerVisitor`:

```python
def visit_Something(self, node: ast.Something) -> None:
    # implementation
    pass
```

Add tests in `tests/test_analyzer.py`.

## Submitting Changes

1. Create a feature branch
2. Make your changes with tests
3. Run `pytest` to ensure all tests pass
4. Open a pull request with a clear description

## Reporting Bugs

Open an issue at https://github.com/aravindadityxa/codemedic/issues with:

- Python version
- CodeMedic version (`codemedic version`)
- Minimal reproducible example
- Expected vs actual behaviour
