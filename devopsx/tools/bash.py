"""
The assistant can execute shell commands by outputting code blocks with `b` or `bash` as the language.
"""

import sys
import invoke
import logging
import getpass
from collections.abc import Generator

from ..message import Message
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
password = None

def execute_bash(cmd: str, sudo: bool = False, pty: bool = True)-> Generator[Message, None, None]:
    try:
        if sudo or cmd.lstrip().startswith("sudo"):
            global password
            if password is None: password = getpass.getpass(prompt="[sudo] password: ")
            result = invoke.sudo(cmd, pty=True, warn=True, password=password)
        else:    
            if pty: result = invoke.run(cmd, pty=True, warn=True)
            else: result = invoke.run(cmd)

        sys.stdout.flush()
        print()

        stdout = _shorten_stdout(result.stdout.strip())
        stderr = _shorten_stdout(result.stderr.strip())

        stdout = stdout.replace("[sudo] password:", "")

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
