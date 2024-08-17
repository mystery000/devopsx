"""
Tool for the assistant to manage subagents  
"""

import os
import re
import sys
import logging
import getpass
import paramiko
from typing import Literal
from tabulate import tabulate
from paramiko import SSHClient
from configparser import ConfigParser
from collections.abc import Generator
from fabric import Connection, Result

from .base import ToolSpec
from ..message import Message
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)

instructions = f"""
When you send a message containing bash code, it will be executed in a pseudo terminal.
The shell will respond with the output of the execution.
Do not use EOF/HereDoc syntax to send multiline commands, as the assistant will not be able to handle it.
Do not include the string "```" in the assistant messages.
""".strip()

examples = f"""
USER: /subagent 
ASSISTANT: It seems you want to manage subagents. Here are the available commands:

1. Add a new subagent:
   /subagent add <agent_id> [-i identity_file] [-p port] <user@host>

2. Delete an existing subagent:
   /subagent delete <agent_id>

3. List all subagents:
   /subagent list

4. Get the status of a specified agent:
   /subagent status <agent_id>

5. Execute a shell command on a specified agent:
   /subagent shell <agent_id> <command>
""".strip()

MAX_TIMEOUT = 4

# Define the path to the config file 
config_path = os.path.expanduser("~/.config/devopsx/subagents")

actions: dict[str, dict[str, str]] = {
    "add": { "description": "Register a new subagent", "format": "/subagent add <agent_id> [-i identity_file] [-p port] <user@host>" },
    "delete": { "description": "Remove an existing subagent", "format": "/subagent delete <agent_id>" },
    "list": { "description": "List all subagents", "format": "/subagent list" },
    "status": { "description": "Get the status of the specified agent", "format": "/subagent status <agent_id>" },
    "shell": { "description": "Execute a shell command on a specified agent", "format": "/subagent shell <agent_id> <command>"},
}

COMMANDS = set(actions.keys())

_config: ConfigParser | None = None
_subagents: dict[str, Connection] = dict()

def init_tool() -> None:
    # Check if the config file exists
    if not os.path.exists(config_path):
        # If not, create it and write some default settings
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        os.mknod(config_path)
        logger.info(f"A subagents configuration file has been successfully created at {config_path}.") 
    
    global _config
    _config = ConfigParser()
        
def check_connection(host: str, user: str, port: int, identity_file: str | None = None, password: str | None = None) -> bool:
    ssh_client = SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if identity_file:
            private_key_path = os.path.expanduser(identity_file)
            private_key = paramiko.RSAKey.from_private_key_file(private_key_path)
            ssh_client.connect(hostname=host, port=port, username=user, timeout=MAX_TIMEOUT, pkey=private_key)
        else:
            if not password: password = getpass.getpass(prompt=f"{user}@{host}'s password: ")
            ssh_client.connect(host, port, username=user, password=password, timeout=MAX_TIMEOUT, look_for_keys=False, allow_agent=False)
    except Exception as ex:
        logger.error(str(ex))
        return False
    finally:
        ssh_client.close()
    
    return True


def add_subagent(agent_id: str, user: str, host: str, port: int = 22, identity_file: str | None = None):
    _config.read(config_path)
    
    agent_id = agent_id.upper()
    
    if agent_id in _config:
        yield Message("system", "Already registered.")
    else:
        agent = {}

        if identity_file and check_connection(host, user, port, identity_file):
            agent.update({ "Hostname": host, "User": user, "Port": port })
            agent["PasswordAuthentication"] = "no"
            agent["IdentityFile"] = identity_file
        elif not identity_file and check_connection(host, user, port):
            agent.update({ "Hostname": host, "User": user, "Port": port })
            agent["PasswordAuthentication"] = "yes"

        if agent:
            _config[agent_id] = agent
            with open(config_path, 'w') as file:
                _config.write(file)
            yield Message("system", "Successfully registered")
        else:
            yield Message("system", "Subagent registration failed.")

    
def delete_subagent(agent_id: str) -> Generator[Message, None, None]:
    _config.read(config_path)
    agent_id = agent_id.upper()

    if agent_id in _config:
        del _config[agent_id]
        if agent_id in _subagents: del _subagents[agent_id]
        with open(config_path, 'w') as config_file:
            _config.write(config_file)
        yield Message("system", f"{agent_id} agent is removed successfully.")
    else:
        yield Message("system", f"The specific agent is not registered, so we're unable to execute your command.")


def execute_shell(agent_id: str, shell_command: str) -> Generator[Message, None, None]:
    _config.read(config_path)
    agent_id = agent_id.upper()
    
    if not agent_id in _config:
        yield Message("system", "The specific agent is not registered, so we're unable to execute your command.")
        return
    
    connection: Connection = None

    global _subagents
    agent = _config[agent_id]

    if agent_id not in _subagents:
        host, user, port = agent["Hostname"], agent["User"], agent["Port"]
        if _config.getboolean(agent_id, "PasswordAuthentication") is True:
            password = getpass.getpass(prompt=f"{user}@{host}'s password: ")
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
            identity_file = agent["IdentityFile"]
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
        connection = _subagents[agent_id]


    if not connection:
        yield Message("system", f"We're currently unable to execute your command. Please verify the status of your subagent using `{actions['status']['format']}`.")
        return

    result: Result = None

    if shell_command.strip().startswith("sudo"):
        result = connection.sudo(shell_command, pty=True, warn=True)
    else:    
        result = connection.run(shell_command, pty=True, warn=True)
    
    # Sends keepalive packets every 60 seconds to keep connections alive
    connection.client.get_transport().set_keepalive(60)  
    
    _subagents[agent_id] = connection

    sys.stdout.flush()
    print()

    stdout = _shorten_stdout(result.stdout.strip())
    stderr = _shorten_stdout(result.stderr.strip())

    content = _format_block_smart("Ran command", shell_command, lang="bash") + "\n\n"
    
    if stdout:
        content += _format_block_smart("stdout", stdout) + "\n\n"
    if stderr:
        content += _format_block_smart("stderr", stderr) + "\n\n"
    if not stdout and not stderr:
        content += "No output\n"

    yield Message("system", content)
 

def list_agents() -> Generator[Message, None, None]:
    _config.read(config_path)
    
    table = []
    headers = ["AGENT_ID", "HOST", "USER", "PORT", "PASSWORD_AUTHENTICATION", "IDENTITY_FILE"]
    
    for agent_id, agent in _config.items():
        table.append([agent_id] + [value for _, value in agent.items()])
    
    yield Message("system", tabulate(table[1:], headers, tablefmt="grid", showindex="always"))
        
    
def get_status_agent(agent_id: str) -> str:
    _config.read(config_path)
    agent_id = agent_id.upper()
    
    if not agent_id in _config: return "Not Registered"
    return "Connected" if agent_id in _subagents else "Disconnected"

        
def execute_subagent(cmd: str) -> Generator[Message, None, None]:
    type, *args = cmd.strip().split(sep=" ", maxsplit=1)
    
    if type == "list": args.append("list")
    if not type or not args:
        print("Invalid command format. Here are the available commands: ")
        table = []
        headers = ["COMMAND", "DESCRIPTION", "FORMAT"]
        
        for command, action in actions.items():
            table.append([command] + [value for _, value in action.items()])
        yield Message("system", tabulate(table, headers, tablefmt="grid", showindex="always"))
        return
        
    command = args[0]
    match type:
        case "add":
            pattern = re.compile(r'(?P<agent_id>\S+)\s+(-i\s+(?P<identity_file>\S+)\s+)?(-p\s+(?P<port>\d+)\s+)?(?P<user>\S+)@(?P<host>\S+)')                     
            match = pattern.match(command)
                                                                                                                              
            if not match:                                                                                                                                                   
                yield Message("system", f"Invalid format. usage: `{actions['add']['format']}`")                                                
                                                                                                                                                                            
            agent_id = match.group('agent_id')                                                                                                                              
            identity_file = match.group('identity_file')                                                                                                                    
            user = match.group('user')                                                                                                                              
            host = match.group('host')                                                                                                                                      
            port = int(match.group('port')) if match.group('port') else 22

            if not agent_id or not user or not host or not port:
                yield Message("system", "Incorrect command. Try again.")
            yield from add_subagent(agent_id, user, host, port, identity_file)
        case "delete":
            pattern = re.compile(r'(?P<agent_id>\S+)')
            match = pattern.match(command)

            if not match:
                yield Message("system", f"Invalid format. Usage: `{actions['delete']['format']}`")
                return
            
            agent_id = match.group('agent_id')
            
            if not agent_id:
                yield Message("system", "Incorrect command. Try again.")
                return

            yield from delete_subagent(agent_id)
        case "shell" | "bash" | "sh":
            shell_pattern = re.compile(r'(?P<agent_id>\S+)\s+(?P<command>.+)')
            match = shell_pattern.match(command)

            if not match:
                yield Message("system", f"Invalid format. Usage: `{actions['shell']['format']}`")
                return
            
            agent_id = match.group('agent_id')
            shell_command = match.group('command')
            
            if not agent_id or not shell_command:
                yield Message("system", "Incorrect command. Try again.")
                return

            yield from execute_shell(agent_id, shell_command)
        case "list":
            yield from list_agents()
        case "status":
            pattern = re.compile(r'(?P<agent_id>\S+)')
            match = pattern.match(command)

            if not match:
                yield Message("system", f"Invalid format. Usage: `{actions['status']['format']}`")
                return
            
            agent_id = match.group('agent_id')
            
            if not agent_id:
                yield Message("system", "Incorrect command. Try again.")
                return
            
            yield Message("system", tabulate([[agent_id, get_status_agent(agent_id)]], ["AGENT_ID", "STATUS"], tablefmt="grid"))
        case _:
            print("Unknown command. To see the available commands, run `/subagent`")
            return


tool = ToolSpec(
    name="subagent",
    desc="Manage subagents",
    instructions=instructions,
    examples=examples,
    init=init_tool,
    execute=execute_subagent,
    block_types=["subagent"],
)       