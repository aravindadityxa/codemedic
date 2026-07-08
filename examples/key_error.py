"""Example: KeyError – missing dictionary key."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
user = {"name": "Alice", "email": "alice@example.com"}
print(user["age"])   # KeyError: 'age'
""",
    filename="key_error_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Fix: {fix.description}")
