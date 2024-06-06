import os
import logging
import requests
import configparser
from collections.abc import Generator

from ..message import Message
from .celery import devopsx_reply
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)
 
password = None

# Define the path to the config file 
config_path = os.path.expanduser("~/.config/devopsx/agents")

def init_agents() -> None:
    # Check if the config file exists
    if not os.path.exists(config_path):
        # If not, create it and write some default settings
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        os.mknod(config_path)
        logger.info(f"Created agents config file at {config_path}")
    
def execute_remote_agent(cmd, sudo=False)-> Generator[Message, None, None]:
    try:

        if len(cmd.split(" ")) < 2:
            raise SyntaxError("Invalid command format. The format should be `/ra <host> <command>`")

        hostname, command = cmd.split(" ", 1)
        hostname = hostname.upper()

        result = devopsx_reply.apply_async(args=[command], queue=hostname, routing_key=f'{hostname.lower()}.devopsx.reply')

        if result.ready():
            message = result.get()
            yield Message("system", content=message)

        # config = configparser.ConfigParser()
        # config.read(config_path)

        # if hostname not in config:
        #    raise LookupError("The specific host is not registered. You should add it using this command. `/ssh <hostname> <user@host> [identity_file]`")

        # url = f'https://f6f9-5-8-93-225.ngrok-free.app/api/conversations/agent/generate'

        # response = requests.post(url, json={
        #     "command": command
        # })

        # if response.status_code  == 200:
        #     msgs = response.json()
        #     for msg in msgs: print(msg["content"])
        # else:
        #     print(f"Request failed with status code: {response.status_code}")
        

    except Exception as ex:
        yield Message("system", content=f"Error: {ex}")