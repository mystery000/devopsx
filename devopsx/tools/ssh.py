import sys
import yaml
import logging
from collections.abc import Generator

from ..message import Message

logger = logging.getLogger(__name__)


def execute_ssh(cmd: str, ask=True)-> Generator[Message, None, None]:
    yield Message("system", cmd)