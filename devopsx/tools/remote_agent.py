import os
import logging
from collections.abc import Generator

from ..message import Message
# from ..celery import chat

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

def execute_remote_agent(cmd, sudo = False)-> Generator[Message, None, None]:
    try:
        if len(cmd.split(" ")) < 2:
            raise SyntaxError("Invalid command format. The format should be `/ra <host> <command>`")

        hostname, command = cmd.split(" ", 1)
        hostname = hostname.upper()

        # result = chat.apply_async(args=[command], queue=hostname, routing_key=f'{hostname.lower()}.chat')
        result = ""

        yield Message("system", content=result.get(propagate=False))

    except Exception as ex:
        yield Message("system", content=f"Error: {ex}")