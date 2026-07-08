"""Example: ZeroDivisionError."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
total = 100
count = 0
average = total / count   # ZeroDivisionError: division by zero
""",
    filename="zero_division_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    print("Analogy:", result.explanation["analogy"])
    for fix in result.fixes:
        print(f"Fix: {fix.description}")
