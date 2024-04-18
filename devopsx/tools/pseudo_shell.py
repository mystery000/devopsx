import sys
import logging
import getpass
from paramiko import SSHConfig
from fabric import Connection, Result
from collections.abc import Generator

from ..message import Message
from .ssh import config_path, check_connection
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
_connections: dict[str, Connection] = dict()

def execute_pseudo_shell(cmd, sudo=False)-> Generator[Message, None, None]:
    try:
        if len(cmd.split(" ")) < 2:
            raise SyntaxError("Invalid command format. The format should be `/ps <host> <command>`")
        
        hostname, command = cmd.split(" ", 1)
        ssh_config = SSHConfig()
        ssh_config.parse(open(config_path))
        config = ssh_config.lookup(hostname.upper())

        if config["hostname"] == hostname.upper():
            raise ValueError("Unregistered Host")
        
        connection: Connection = None

        global _connections
        key = config["hostname"].replace(".", "")

        if f"{key}" not in _connections:
            if config.as_bool("passwordauthentication") is True:
                host, user, port = config["hostname"], config["user"], config["port"]
                password = getpass.getpass(prompt="Password: ")
                if check_connection(host, user, port, password=password):
                    connection = Connection(
                        host=host, 
                        user=user, 
                        port=port,
                        connect_kwargs={
                            "password": password
                        }
                    )
                    _connections[f"{key}"] = connection
            else:
                host, user, port, identity_files = config["hostname"], config["user"], config["port"], config["identityfile"]
                for identity_file in identity_files:
                    if check_connection(host, user, port, identity_file):
                        connection = Connection(
                            host=host, 
                            user=user, 
                            port=port,
                            connect_kwargs={
                                "key_filename": identity_file,
                            }
                        )
                        _connections[f"{key}"] = connection
                        break
        else:
            connection = _connections[f"{key}"]


        assert connection is not None

        result: Result = None

        if sudo or command.lstrip().startswith("sudo"):
            result = connection.sudo(command, pty=True, warn=True)
        else:    
            result = connection.run(command, pty=True, warn=True)
        
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
    