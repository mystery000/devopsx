import logging
from fabric import Connection
from collections.abc import Generator

from ..message import Message
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
_connections: dict[str, Connection] = dict()

def get_connection(hostname: str, port: int, username: str, password: str) -> Connection:
    global _connections
    key = hostname.replace(".", "")
    if f"{key}" not in _connections:
        _connections[f"{key}"] = Connection(f"{username}@{hostname}:{port}", connect_kwargs={"password": f"{password}"})
    return _connections[f"{key}"]

def execute_pseudo_shell(cmd: str, ask=True, sudo=True)-> Generator[Message, None, None]:
    hostname = "213.156.159.139"
    username = "devopsx"
    password = "devopsx"
    try:
        connection = get_connection(hostname, 22, username, password)

        # sudopass = Responder(
        #     pattern=r"\[sudo\] password:",
        #     response="devopsx"
        # )

        result = connection.run(cmd, pty=True, warn=True)

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
    except Exception as e:
        yield Message("system", content=f"Error: {e}")
