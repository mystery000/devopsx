"""
Gives the assistant the ability to save code to a file.

Example:

.. chat::

    User: write hello world to hello.py
    Assistant:
    ```hello.py
    print("hello world")
    ```
    System: Saved to hello.py
"""

from collections.abc import Generator
from pathlib import Path

from ..message import Message, print_msg
from ..util import ask_execute

from .python import execute_python
from .shell import execute_shell

def execute_file(
        fn: str, code: str, ask: bool
) -> Generator[Message, None, None]:
    """Execute the file"""
    if fn.endswith(".py"): 
        yield from execute_python(code, ask=ask)
    elif fn.endswith(".sh"):
        yield from execute_shell(code, ask=ask)

def execute_save(
    fn: str, code: str, ask: bool, append: bool = False
) -> Generator[Message, None, None]:
    """Save the code to a file."""
    action = "save" if not append else "append"
    # strip leading newlines
    code = code.lstrip("\n")

    if ask:
        confirm = ask_execute(f"{action.capitalize()} to {fn}?")
        print()
    else:
        confirm = True
        print(f"Skipping {action} confirmation.")

    if ask and not confirm:
        # early return
        print_msg(Message("system", f"{action.capitalize()} cancelled."))
        yield from execute_file(fn, code, ask)
        return

    path = Path(fn).expanduser()

    if append:
        if not path.exists():
            yield Message("system", f"File {fn} doesn't exist, can't append to it.")
            return

        with open(path, "a") as f:
            f.write(code)
        yield Message("system", f"Appended to {fn}")
        return

    # if the file exists, ask to overwrite
    if path.exists():
        if ask:
            overwrite = ask_execute("File exists, overwrite?")
            print()
        else:
            overwrite = True
            print("Skipping overwrite confirmation.")
        if not overwrite:
            # early return
            print_msg(Message("system", "Save cancelled."))
            yield from execute_file(fn, code, ask)
            return

    # if the folder doesn't exist, ask to create it
    if not path.parent.exists():
        if ask:
            create = ask_execute("Folder doesn't exist, create it?")
            print()
        else:
            create = True
            print("Skipping folder creation confirmation.")
        if create:
            path.parent.mkdir(parents=True)
        else:
            # early return
            print_msg(Message("system", "Save cancelled."))
            yield from execute_file(fn, code, ask)
            return

    print("Saving to " + fn)
    with open(path, "w") as f:
        f.write(code)
    yield Message("system", f"Saved to {fn}")
