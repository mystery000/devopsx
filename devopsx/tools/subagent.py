"""
Tool for the assistant to manage subagents  
"""

import os
import re
import sys
import rich
import logging
import getpass
import paramiko
import threading
from typing import Literal
from paramiko import SSHClient
from configparser import ConfigParser
from collections.abc import Generator
from fabric import Connection, Result

from .base import ToolSpec, ToolUse
from ..message import Message
from .shell import _shorten_stdout, _format_block_smart
from ..message import Message, print_msg
from ..util import ask_execute, print_preview

logger = logging.getLogger(__name__)

MAX_TIMEOUT = 4

# Define the path to the config file 
config_path = os.path.expanduser("~/.config/devopsx/subagents")

actions: dict[str, dict[str, str]] = {
    "add": { "description": "Register a new subagent", "usage": "/subagent add <agent_id> [-i identity_file] [-p port] <user@host>" },
    "delete": { "description": "Remove an existing subagent", "usage": "/subagent delete <agent_id>" },
    "list": { "description": "List all subagents", "usage": "/subagent list" },
    "shell": { "description": "Execute a shell command on a specified agent", "usage": "/subagent shell <agent_id> <command>"},
}

COMMANDS = set(actions.keys())

subagent_commands_str = "\n".join(f"- {action}: {details['description']}, usage: {details['usage']}" for action, details in actions.items())

instructions = f"""
You can utilize the subagent tool to manage subagents registered with devopsx and execute shell commands in the terminal of a subagent.  
When you send a message containing bash code, it will be executed in a pseudo terminal.
The shell will respond with the output of the execution.
Do not use EOF/HereDoc syntax to send multiline commands, as the assistant will not be able to handle it.

Available commands:
{subagent_commands_str}
""".strip()

examples = f"""
USER: add a new subagent
ASSISTANT: Sure! To add a new subagent, you'll need to provide the following details:
- Agent ID
- Host
- User
- Port (optional, default is 22)
- Identity file (optional, if using key-based authentication)
- Password authentication (optional, if using password-based authentication)

Once you provide these details, I'll generate the command for you. 😊
USER: Agent ID is Master, User is debian, Host is master.infractura.com.
ASSISTANT: Great! Let's add the new subagent with the provided details. Here is the command to do so:
```ps
/subagent add MASTER debian@master.infractura.com
```

USER: list all registered subagents
ASSISTANT: To list all registered subagents, you can use the following command:
```ps
/subagent list
```

USER: list the current directory in DEV agent
ASSISTANT: To list the files in the current directory, use `ls`:
```ps
/subagent shell DEV ls
```
System: Ran command: `ls`
```stdout
file1.txt
file2.txt
```
#### The assistant can recognize that user is executing shell commands on a DEV agent.
User: What is the hostname of agent?
Assistant: To get the hostname, use `hostname`:
```ps
/subagent shell DEV hostname
```
System: Ran command: `hostname`
```stdout
debian
```

#### The assistant is capable of executing identical commands on multiple agents at the same time.  
USER: get the status of 'w' from all the subagents.
ASSISTANT: To get the status of the 'w' command from all the subagents. we can execute the 'w' command on each subagent. Here are the comamnds to do so:
```ps
/subagent shell agent1 w
/subagent shell agent2 w
/subagent shell agent3 w
/subagent shell agent4 w
/subagent shell agent5 w
/subagent shell agent6 w
/subagent shell agent7 w
/subagent shell agent8 w
```
""".strip()

_config: ConfigParser | None = None
_subagents: dict[str, Connection] = dict()

def init_tool() -> ToolSpec:
    # Check if the config file exists
    if not os.path.exists(config_path):
        # If not, create it and write some default settings
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        os.mknod(config_path)
        logger.info(f"A subagents configuration file has been successfully created at {config_path}.") 
    
    global _config
    _config = ConfigParser()

    return tool
        

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

    content = _format_block_smart("Ran command", f"/subagent shell {agent_id} {shell_command}", lang="bash") + "\n\n"
    
    if len(shell_command) >= 2:
        if (shell_command.startswith("'") and shell_command.endswith("'")) or (shell_command.startswith('"') and shell_command.endswith('"')):
            shell_command = shell_command[1:-1]

    if not agent_id in _config:
        error_msg = f"Error: The specific agent is not registered. Please check its existence using `{actions['list']['usage']}`.\n\n"
        yield Message("system", content + error_msg)
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
        error_msg = f"Error: Unable to establish a connection with the {agent_id}. \n\n"
        yield Message("system", content + error_msg)
        return

    result: Result = None

    shell_command = shell_command.strip()
    if shell_command.startswith("sudo"):
        result = connection.sudo(shell_command, pty=True, warn=True)
    else:    
        result = connection.run(shell_command, pty=True, warn=True)
    
    # Sends keepalive packets every 60 seconds to keep connections alive
    connection.client.get_transport().set_keepalive(60)  
    
    _subagents[agent_id] = connection

    sys.stdout.flush()
    print()

    stdout = _shorten_stdout(result.stdout.strip(), pre_tokens=2000, post_tokens=8000)
    stderr = _shorten_stdout(result.stderr.strip(), pre_tokens=2000, post_tokens=2000)

    if stdout:
        content += _format_block_smart("stdout", stdout) + "\n\n"
    if stderr:
        content += _format_block_smart("stderr", stderr) + "\n\n"
    if not stdout and not stderr:
        content += "No output\n"

    yield Message("system", content)
 

def list_agents() -> Generator[Message, None, None]:
    _config.read(config_path)
    msg = ""
    for agent_id, agent in _config.items():
        if agent_id.upper() == "DEFAULT": continue
        msg += f"""
- {agent_id}
  hostname: {agent.get("hostname")},
  user: {agent.get("user")},
  port: {agent.get("port")},
  password_authentication: {agent.get("passwordauthentication")},
  identity_file: {agent.get("identityfile")}
  """
    
    yield Message("system", msg)
        

def run_subagent_thread(cmd: str, msgs: list[Message]):
    response = execute_subagent(cmd, ask=False, args=[])
    for msg in response: msgs.append(msg)


def execute_subagent(cmd: str, ask: bool, args: list[str]) -> Generator[Message, None, None]:
    cmd = cmd.strip()
    confirm = True
    if ask:
        print_preview(f"Command: {cmd}", "bash")
        confirm = ask_execute()
        print()
        if not confirm:
            print_msg(Message("system", "Aborted, user chose not to run command."))
            return

    if cmd.count("/subagent") > 1:
        msgs: list[Message] = []
        commands = cmd.splitlines()
        
        threads: list[threading.Thread] = []

        # Create and start multiple threads
        for command in commands:
            thread = threading.Thread(target=run_subagent_thread, args=(command, msgs), daemon=True)
            threads.append(thread)
            thread.start() 

        try:
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=60) # Waits for a thread to finish. Timeout is 1 minute.
        except KeyboardInterrupt:
            print("KeyboardInterrupt received, stopping threads...")
            for thread in threads:
                thread.join(timeout=1)
            print("Threads have been stopped gracefully.")

        yield Message("system", "\n".join(msg.content for msg in msgs))            
        return

    cmd = cmd.removeprefix("/subagent")
    type, *args = cmd.strip().split(sep=" ", maxsplit=1)
    
    if type == "list": args.append("list")
    if not type or not args:
        print("Invalid command format. Here are the available commands: ")
        msg = ""
        for command, action in actions.items():
            msg += f"""
- {command}  ({action.get("description")})
    usage: {action.get("usage")}
    """

        yield Message("system", msg)
        return
        
    command = args[0]
    match type:
        case "add":
            pattern = re.compile(r'(?P<agent_id>\S+)\s+(-i\s+(?P<identity_file>\S+)\s+)?(-p\s+(?P<port>\d+)\s+)?(?P<user>\S+)@(?P<host>\S+)')                     
            match = pattern.match(command)
                                                                                                                              
            if not match:                                                                                                                                                   
                yield Message("system", f"Invalid format. usage: `{actions['add']['usage']}`")                                                
                                                                                                                                                                            
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
                yield Message("system", f"Invalid format. Usage: `{actions['delete']['usage']}`")
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
                yield Message("system", f"Invalid format. Usage: `{actions['shell']['usage']}`")
                return
            
            agent_id = match.group('agent_id')
            shell_command = match.group('command')
            
            if not agent_id or not shell_command:
                yield Message("system", "Incorrect command. Try again.")
                return

            yield from execute_shell(agent_id, shell_command)
        case "list":
            yield from list_agents()
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
    block_types=["ps"],
)       
__doc__ = tool.get_doc(__doc__)