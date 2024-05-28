import logging
import requests
import configparser
from collections.abc import Generator

from ..message import Message

from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
password = None

def execute_remote_agent(cmd, sudo=False)-> Generator[Message, None, None]:
    from .ssh import config_path
    try:
        if len(cmd.split(" ")) < 2:
            raise SyntaxError("Invalid command format. The format should be `/ra <host> <command>`")

        hostname, command = cmd.split(" ", 1)
        hostname = hostname.upper()
        
        config = configparser.ConfigParser()
        config.read(config_path)

        if hostname not in config:
           raise LookupError("The specific host is not registered. You should add it using this command. `/ssh <hostname> <user@host> [identity_file]`")

        url = f'http://{config[hostname]["hostname"]}:5000/api/conversations/agent/generate'

        response = requests.post(url, json={
            "command": command
        })

        if response.status_code  == 200:
            msgs = response.json()
            for msg in msgs: print(msg["content"])
        else:
            print(f"Request failed with status code: {response.status_code}")

    except Exception as ex:
        yield Message("system", content=f"Error: {str(ex)}")
    