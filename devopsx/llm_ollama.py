import logging
from ollama import Client, Options
from collections.abc import Generator

from .constants import TEMPERATURE, TOP_P
from .message import Message, msgs2dicts

ollama_client: Client | None = None
logger = logging.getLogger(__name__)


def init(config):
    global ollama_client
    ollama_host = config.get_env_required("OLLAMA_HOST")
    ollama_client = Client(host=ollama_host, timeout=120)


def get_client() -> Client | None:
    return ollama_client


def chat(messages: list[Message], model: str) -> str:
    assert ollama_client, "LLM not initialized"
    response = ollama_client.chat(
        model=model,
        messages=[messages[0].to_dict(keys=["role", "content"]), *msgs2dicts(messages[1:], ollama=True)],
        options=Options(
            temperature=TEMPERATURE,
            top_p=TOP_P
        )
    )
    content = response['message']['content']
    assert content
    return content


def stream(messages: list[Message], model: str) -> Generator[str, None, None]:
    assert ollama_client, "LLM not initialized"
    for chunk in ollama_client.chat(
        model=model,
        messages=[messages[0].to_dict(keys=["role", "content"]), *msgs2dicts(messages[1:], ollama=True)],
        stream=True,
        options=Options(
            temperature=TEMPERATURE,
            top_p=TOP_P
        )
    ): yield chunk['message']['content']