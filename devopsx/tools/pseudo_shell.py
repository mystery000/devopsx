import os
import sys
import logging
from paramiko import SSHConfig
from fabric import Connection, Result
from collections.abc import Generator

from ..message import Message
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
# Define the path to the config file
config_path = os.path.expanduser("~/.config/devopsx/ssh_servers.config")

_connections: dict[str, Connection] = dict()

def execute_pseudo_shell(server_name:str, cmd: str, sudo=True)-> Generator[Message, None, None]:
    try:
        ssh_config = SSHConfig()
        ssh_config.parse(open(config_path))
        config = ssh_config.lookup(server_name.upper())

        if config["hostname"] == server_name.upper():
            raise ValueError("This server name is not registered.")
        
        connection: Connection = None

        global _connections
        key = config["hostname"].replace(".", "")

        if f"{key}" not in _connections:
            if config.as_bool("passwordauthentication") is True:
                connection = Connection(
                    host=config["hostname"], 
                    user=config["user"], 
                    port=config["port"],
                    connect_kwargs={
                        "password": config["password"],
                    }
                )
            else:
                connection = Connection(
                    host=config["hostname"], 
                    user=config["user"], 
                    port=config["port"],
                    connect_kwargs={
                        "key_filename": config["identityfile"],
                    }
                )
            _connections[f"{key}"] = connection
        else:
            connection = _connections[f"{key}"]


        result: Result = None

        if sudo or cmd.lstrip().startswith("sudo"):
            result = connection.sudo(cmd, pty=True, warn=True)
        else:    
            result = connection.run(cmd, pty=True, warn=True)
        
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
    except Exception as e:
        yield Message("system", content=f"Error: {e}")
