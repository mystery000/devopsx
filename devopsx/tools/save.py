"""
Gives the assistant the ability to save or append code to a file.

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

from ..message import Message
from ..util import ask_execute
from .base import ToolSpec

instructions = """
To save code to a file, use a code block with the filepath as the language.
""".strip()

examples = """
User: Write a Hello world script to hello.py
Assistatn: Certainly! I'll write a simple "Hello, World!" script and save it to a file named `hello.py`. Here's the code:
```hello.py
print("Hello world!")
```
System: Saved to `hello.py`.

### Realize that the message 'Save cancelled' indicates that the user chose not to save the file. Instead of saving the file directly, show the code so users can decide how to save it.
User: Write a Hello World script to hello.py
Assistatn: Certainly! I'll write a simple "Hello, World!" script and save it to a file named `hello.py`. Here's the code:
```hello.py
print("Hello world!")
```
System: Save cancelled.
Assistant: It looks like the file wasn't saved. Instead, I'll show you the code again, and you can decide how to save it.

Here's the Python script that we can use for `hello.py`
```python
print("Hello world!")
```

User: Create a React component for a basic login page with username and password fields. Save it to `/opt/sites/login.jsx`.
Asistant: I'll create a React component for a basic login page with username and password fields and save it to `/opt/sites/login.jsx`. Here's the code:
```/opt/sites/login.jsx
import React, { useState } from 'react';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Login attempt with:', { username, password });
    // Here you would typically send the login data to your backend
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username">Username:</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="password">Password:</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit">Login</button>
      </form>
    </div>
  );
};

export default LoginPage;
```
System: Saved to login.jsx
""".strip()


def execute_save(
    code: str, ask: bool, args: list[str]
) -> Generator[Message, None, None]:
    """Save code to a file."""
    fn = " ".join(args)
    assert fn, "No filename provided"
    # strip leading newlines
    code = code.lstrip("\n")
    # ensure it ends with a newline
    if not code.endswith("\n"):
        code += "\n"

    if ask:
        confirm = ask_execute(f"Save to {fn}?")
        print()
    else:
        confirm = True
        print("Skipping confirmation.")

    if ask and not confirm:
        # early return
        yield Message("system", "Save cancelled.")
        return

    path = Path(fn).expanduser()

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
            yield Message("system", "Save cancelled.")
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
            yield Message("system", "Save cancelled.")
            return

    print("Saving to " + fn)
    with open(path, "w") as f:
        f.write(code)
    yield Message("system", f"Saved to {fn}")


def execute_append(
    code: str, ask: bool, args: list[str]
) -> Generator[Message, None, None]:
    """Append code to a file."""
    fn = " ".join(args)
    assert fn, "No filename provided"
    # strip leading newlines
    code = code.lstrip("\n")
    # ensure it ends with a newline
    if not code.endswith("\n"):
        code += "\n"

    if ask:
        confirm = ask_execute(f"Append to {fn}?")
        print()
    else:
        confirm = True
        print("Skipping append confirmation.")

    if ask and not confirm:
        # early return
        yield Message("system", "Append cancelled.")
        return

    path = Path(fn).expanduser()

    if not path.exists():
        yield Message("system", f"File {fn} doesn't exist, can't append to it.")
        return

    with open(path, "a") as f:
        f.write(code)
    yield Message("system", f"Appended to {fn}")


tool_save = ToolSpec(
    name="save",
    desc="Save code to a file",
    instructions=instructions,
    examples=examples,
    execute=execute_save,
    block_types=["save"],
)

instructions_append = """
To append code to a file, use a code block with the language: append <filepath>
""".strip()

examples_append = """
User: append a print "Hello world" to hello.py
Assistant:
```append hello.py
print("Hello world")
```
System: Appended to `hello.py`.

User: How to add I add mouse controls on tmux?
Assistant: To enable mouse support in tmux, you need to add the following configuration to your `~/.tmux.conf` file:
```append ~/.tmux.conf
set -g moust on
```
System: File ~/.tmux.conf doesn't exist, can't append to it.
Asistant: Let's create the `~/.tmux.conf` file with the mouse support configuration.
```~/.tmux.conf
set -g mouse on
```
System: Saved to `~/.tmux.conf`
""".strip()

tool_append = ToolSpec(
    name="append",
    desc="Append code to a file",
    instructions=instructions_append,
    examples=examples_append,
    execute=execute_append,
    block_types=["append"],
)