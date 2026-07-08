"""Example: FileNotFoundError."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
with open("data/config.json") as f:   # FileNotFoundError
    content = f.read()
""",
    filename="file_not_found_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Fix: {fix.description}")
