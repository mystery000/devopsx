import os
import logging
from collections.abc import Generator

from .base import ToolSpec
from ..message import Message
# from ..celery import chat

logger = logging.getLogger(__name__)
 
password = None

def init_agents() -> None:
    ...
    
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
        
tool = ToolSpec(
    name="remote agent",
    desc="Run shell commands on remote agents.",
    instructions="",
    examples="",
    init=init_agents,
    execute=execute_remote_agent,
    block_types=["ra"],
)       