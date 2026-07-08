"""Example: AttributeError – method does not exist."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
number = 42
number.upper()   # AttributeError: 'int' object has no attribute 'upper'
""",
    filename="attribute_error_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Fix: {fix.description}")
