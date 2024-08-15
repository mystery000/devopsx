import os
import sys
import logging
import getpass
import configparser
from fabric import Connection, Result
from collections.abc import Generator

from ..message import Message

from .base import ToolSpec
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
_connections: dict[str, Connection] = dict()

instructions = f"""
When you send a message containing bash code, it will be executed in a pseudo terminal.
The shell will respond with the output of the execution.
Do not use EOF/HereDoc syntax to send multiline commands, as the assistant will not be able to handle it.
"""

examples = """
""".strip()

def execute_pseudo_shell(cmd, sudo=False)-> Generator[Message, None, None]:
    from .ssh import config_path, check_connection
    try:
        if len(cmd.split(" ")) < 2:
            raise SyntaxError("Invalid command format. The format should be `/ps <host> <command>`")
        
        hostname, command = cmd.split(" ", 1)
        hostname = hostname.upper()
        
        config = configparser.ConfigParser()
        config.read(config_path)

        if hostname not in config:
            yield Message("system", "The specific host is not registered. You should add it using this command. `/ssh <hostname> <user@host> [identity_file]`")
        
        connection: Connection = None

        global _connections
        host = config[hostname]
        key = host["hostname"].replace(".", "")

        if f"{key}" not in _connections:
            if config.getboolean(hostname, "PasswordAuthentication") is True:
                host, user, port = host["hostname"], host["user"], host["port"]
                password = getpass.getpass(prompt="[sudo] password: ")
                if check_connection(host, user, port, password=password):
                    connection = Connection(
                        host=host, 
                        user=user, 
                        port=port,
                        connect_kwargs={
                            "password": password,
                            "allow_agent": False,
                            "look_for_keys": False
                        }
                    )
            else:
                host, user, port, identity_file = host["hostname"], host["user"], host["port"], host["identityfile"]
                identity_file = os.path.expanduser(identity_file)
                if check_connection(host, user, port, identity_file):
                    connection = Connection(
                        host=host, 
                        user=user, 
                        port=port,
                        connect_kwargs={
                            "key_filename": identity_file,
                        }
                    )
        else:
            connection = _connections[f"{key}"]


        assert connection is not None

        result: Result = None

        if sudo or command.lstrip().startswith("sudo"):
            result = connection.sudo(command, pty=True, warn=True)
        else:    
            result = connection.run(command, pty=True, warn=True)
        
        # Sends keepalive packets every 60 seconds to keep connections alive
        connection.client.get_transport().set_keepalive(60)  
        
        _connections[f"{key}"] = connection

        sys.stdout.flush()
        print()

        stdout = _shorten_stdout(result.stdout.strip())
        stderr = _shorten_stdout(result.stderr.strip())

        msg = _format_block_smart("Ran command", command, lang="bash") + "\n\n"
        
        if stdout:
            msg += _format_block_smart("stdout", stdout) + "\n\n"
        if stderr:
            msg += _format_block_smart("stderr", stderr) + "\n\n"
        if not stdout and not stderr:
            msg += "No output\n"

        yield Message("system", msg)
    except AssertionError:
        yield Message("system", "Authentication failed")
    except Exception as ex:
        yield Message("system", content=f"Error: {str(ex)}")
    
    
tool = ToolSpec(
    name="pseudo shell",
    desc="Executes shell commands in a pseudo terminal",
    instructions="",
    examples=examples,
    init=None,
    execute=execute_pseudo_shell,
    block_types=["ps"],
)