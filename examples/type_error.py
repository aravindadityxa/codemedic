"""Example: TypeError – mixing str and int."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
age = 25
print("Age: " + age)   # TypeError: can only concatenate str (not "int") to str
""",
    filename="type_error_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    print("Analogy:", result.explanation["analogy"])
    for fix in result.fixes:
        print(f"Fix (confidence {fix.confidence:.0%}): {fix.description}")
        print(f"  Suggested: {fix.suggested_line}")
