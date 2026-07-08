# CodeMedic

Intelligent Python debugging library. Explains errors in plain English, identifies root causes, and suggests practical fixes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/codemedic.svg)](https://pypi.org/project/codemedic/)
[![Tests](https://github.com/aravindadityxa/codemedic/actions/workflows/ci.yml/badge.svg)](https://github.com/aravindadityxa/codemedic/actions)

## Features

- **Human-friendly explanations** – Beginner and professional modes
- **Root cause analysis** – Pinpoints the exact file, line, and variable state
- **Fix suggestions** – Non-destructive patch recommendations with confidence scores
- **Static analysis** – 14 AST-based checks for common issues
- **Security scanning** – Detects `eval()`, pickle, hardcoded secrets, weak hashes
- **Multiple report formats** – HTML, JSON, Markdown
- **Terminal UI** – Rich formatting with syntax highlighting
- **Extensible knowledge base** – 40+ built-in exceptions, customizable

## Installation

```bash
pip install codemedic
```

Requires Python 3.11+.

## Usage

### Command Line

Run a script with full error analysis:
```bash
codemedic run script.py
```

Analyze for static issues:
```bash
codemedic analyze script.py
```

Explain an exception:
```bash
codemedic explain TypeError
```

Show system diagnostics:
```bash
codemedic doctor
```

Generate report from a previous result:
```bash
codemedic report --format html --input result.json
```

### Python API

Analyze a file:
```python
from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_file("script.py")

if not result.success:
    print(result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Line {fix.line_number}: {fix.description}")
```

Analyze a callable:
```python
from codemedic import Runner

def process_data():
    return data["key"]

runner = Runner()
result = runner.run_with_capture(process_data)

if not result.success:
    print(result.trace.exception_type)
```

Generate reports:
```python
from codemedic import Runner, ReportGenerator, Config

config = Config(output_folder="./reports")
runner = Runner(config=config)

result = runner.run_file("script.py")
if not result.success:
    gen = ReportGenerator(config)
    gen.generate(result.to_dict(), format="html")
    gen.generate(result.to_dict(), format="json")
```

Static analysis:
```python
from codemedic import CodeAnalyzer

analyzer = CodeAnalyzer()
issues = analyzer.analyze_file("script.py")

for issue in issues:
    print(f"[{issue.severity}] Line {issue.line}: {issue.message}")
```

Security scanning:
```python
from codemedic.security import check_file

warnings = check_file("script.py")
for w in warnings:
    print(f"[{w.code}] {w.message}: {w.recommendation}")
```

## Architecture

- `runner.py` – Script execution and exception capture
- `trace.py` – Stack frame collection and structuring
- `explanations.py` – Explanation generation
- `fixer.py` – Patch suggestion generator
- `analyzer.py` – Static analysis (AST-based checks)
- `security.py` – Security scanning
- `database.py` – SQLite knowledge base (40+ exceptions)
- `formatter.py` – Terminal UI with Rich
- `report.py` – HTML, JSON, Markdown report generation
- `cli.py` – Command-line interface
- `config.py` – Configuration management
- `utils.py` – Shared utilities

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
