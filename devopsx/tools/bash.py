"""
The assistant can execute shell commands by outputting code blocks with `b` or `bash` as the language.
"""

import sys
import invoke
import logging
from collections.abc import Generator

from .base import ToolSpec
from ..message import Message
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)

is_macos = sys.platform == "darwin"

instructions = f"""
When you send a message containing bash code, it will be executed in a stateful bash shell.
The shell will respond with the output of the execution.
Do not use EOF/HereDoc syntax to send multiline commands, as the assistant will not be able to handle it.
{'The platform is macOS.' if is_macos else ''}
""".strip()

examples = """
User: list the current directory
Assistant: To list the files in the current directory, use `ls`:
```bash
ls
```
System: Ran command: `ls`
```stdout
file1.txt
file2.txt
```
#### The assistant can learn context by exploring the filesystem
User: learn about the project
Assistant: Lets start by checking the files
```bash
git ls-files
```
System:
```output
README.md
main.py
```
Assistant: Now lets check the README
```bash
cat README.md
```
System:
```stdout
(contents of README.md)
```
Assistant: Now we check main.py
```bash
cat main.py
```
System:
```output
(contents of main.py)
```
Assistant: The project is...
""".strip()

def execute_bash(cmd: str, sudo: bool = False, pty: bool = True)-> Generator[Message, None, None]:
    try:
        if pty: result = invoke.run(cmd, pty=True, warn=True)
        else: result = invoke.run(cmd)        

        sys.stdout.flush()
        print()

        stdout = _shorten_stdout(result.stdout.strip())
        stderr = _shorten_stdout(result.stderr.strip())

        msg = _format_block_smart("Ran command", cmd, lang="bash") + "\n\n"
        
        if stdout:
            msg += _format_block_smart("stdout", stdout) + "\n\n"
        if stderr:
            msg += _format_block_smart("stderr", stderr) + "\n\n"
        if not stdout and not stderr:
            msg += "No output\n"

        yield Message("system", msg)
    except Exception as ex:
        yield Message("system", content=f"Error: {str(ex)}")


tool = ToolSpec(
    name="bash",
    desc="Executes shell commands.",
    instructions=instructions,
    examples=examples,
    init=None,
    execute=execute_bash,
    block_types=["bash", "b"],
)