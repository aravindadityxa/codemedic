"""Example: IndexError – out-of-range list access."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
fruits = ["apple", "banana", "cherry"]
print(fruits[10])   # IndexError: list index out of range
""",
    filename="index_error_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Fix (confidence {fix.confidence:.0%}): {fix.description}")
