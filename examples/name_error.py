"""Example: NameError – undefined variable."""

from codemedic import Runner

runner = Runner(mode="beginner")
result = runner.run_code(
    """
name = "Alice"
print(nme)   # NameError: name 'nme' is not defined
""",
    filename="name_error_example.py",
)

if not result.success:
    print("Explanation:", result.explanation["simple_explanation"])
    for fix in result.fixes:
        print(f"Fix: {fix.description}")
