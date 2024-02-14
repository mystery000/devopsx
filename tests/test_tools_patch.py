from devopsx.tools.patch import apply

example_patch = """
```patch filename.py
<<<<<<< ORIGINAL
original lines
=======
modified lines
>>>>>>> UPDATED
```
"""


def test_apply_simple():
    codeblock = example_patch
    content = """original lines"""
    result = apply(codeblock, content)
    assert result == """modified lines"""


def test_apply_function():
    content = """
def hello():
    print("hello")

if __name__ == "__main__":
    hello()
"""

    codeblock = """
```patch test.py
<<<<<<< ORIGINAL
def hello():
    print("hello")
=======
def hello(name="world"):
    print(f"hello {name}")
>>>>>>> UPDATED
```
"""

    result = apply(codeblock, content)
    assert result.startswith(
        """
def hello(name="world"):
    print(f"hello {name}")
"""
    )

    # only remove code in patch
    codeblock = """
```patch test.py
<<<<<<< ORIGINAL
def hello():
    print("hello")
=======
>>>>>>> UPDATED
```
"""
    print(content)
    result = apply(codeblock, content)
    newline = "\n"
    newline_escape = "\\n"
    assert result.startswith(
        "\n\n"
    ), f"result: {result.replace(newline, newline_escape)}"
