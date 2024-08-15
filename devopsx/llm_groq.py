import logging
from groq import Groq
from collections.abc import Generator

from .constants import TEMPERATURE, TOP_P
from .message import Message, msgs2dicts

groq: Groq | None = None
logger = logging.getLogger(__name__)


def init(config):
    global groq
    api_key = config.get_env_required("GROQ_API_KEY")
    groq = Groq(
        api_key=api_key,
        max_retries=5
    )


def get_client() -> Groq | None:
    return groq


def chat(messages: list[Message], model: str) -> str:
    # This will generate code and such, so we need appropriate temperature and top_p params
    # top_p controls diversity, temperature controls randomness
    assert groq, "LLM not initialized"
    response = groq.chat.completions.create(
        model=model,
        messages=msgs2dicts(messages),  # type: ignore
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    content = response.choices[0].message.content
    assert content
    return content


def stream(messages: list[Message], model: str) -> Generator[str, None, None]:
    assert groq, "LLM not initialized"
    stop_reason = None
    for chunk in groq.chat.completions.create(
        model=model,
        messages=msgs2dicts(messages),  # type: ignore
        temperature=TEMPERATURE,
        top_p=TOP_P,
        stream=True,
        # the llama-cpp-python server needs this explicitly set, otherwise unreliable results
        # TODO: make this better
        max_tokens=4096
    ):
        if not chunk.choices:  # type: ignore
            # Got a chunk with no choices, Azure always sends one of these at the start
            continue
        stop_reason = chunk.choices[0].finish_reason  # type: ignore
        content = chunk.choices[0].delta.content  # type: ignore
        if content:
            yield content
    logger.debug(f"Stop reason: {stop_reason}")