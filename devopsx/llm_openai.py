import logging
from collections.abc import Generator
from openai import AzureOpenAI, OpenAI

from .constants import TEMPERATURE, TOP_P
from .message import Message, msgs2dicts
from .models import ModelMeta, get_model

openai: OpenAI | None = None
logger = logging.getLogger(__name__)


def init(llm: str, config):
    global openai

    if llm == "openai":
        api_key = config.get_env_required("OPENAI_API_KEY")
        openai = OpenAI(api_key=api_key)
    elif llm == "azure":
        api_key = config.get_env_required("AZURE_OPENAI_API_KEY")
        azure_endpoint = config.get_env_required("AZURE_OPENAI_ENDPOINT")
        openai = AzureOpenAI(
            api_key=api_key,
            api_version="2023-07-01-preview",
            azure_endpoint=azure_endpoint,
        )
    elif llm == "openrouter":
        api_key = config.get_env_required("OPENROUTER_API_KEY")
        openai = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    elif llm == "local":
        api_base = config.get_env_required("OPENAI_API_BASE")
        api_key = config.get_env("OPENAI_API_KEY") or "ollama"
        openai = OpenAI(api_key=api_key, base_url=api_base)
    else:
        raise ValueError(f"Unknown LLM: {llm}")

    assert openai, "LLM not initialized"

def get_client() -> OpenAI | None:
    return openai

def _get_provider_name() -> str:
    client = get_client()
    assert client, "LLM not initialized"
    providers = ["openai", "openrouter", "azure"]
    for provider in providers:
        if provider in str(client.base_url):
            return provider
    return "unknown"

# WIP: maybe remove/move elsewhere? move to models.py?
def list_models() -> Generator[ModelMeta, None, None]:
    client = get_client()
    if not client:
        return
    provider = _get_provider_name()
    for model in client.models.list():
        yield get_model(f"{provider}/{model}")

def _prep_o1(msgs: list[Message]) -> Generator[Message, None, None]:
    # prepare messages for OpenAI O1, which doesn't support the system role
    # and requires the first message to be from the user
    for msg in msgs:
        if msg.role == "system":
            msg = msg.replace(
                role="user", content=f"<system>\n{msg.content}\n</system>"
            )
        yield msg

def chat(messages: list[Message], model: str) -> str:
    # This will generate code and such, so we need appropriate temperature and top_p params
    # top_p controls diversity, temperature controls randomness
    assert openai, "LLM not initialized"
    response = openai.chat.completions.create(
        model=model,
        messages=msgs2dicts(messages, openai=True),  # type: ignore
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    content = response.choices[0].message.content
    assert content
    return content

def reasoning_chat(messages: list[Message], model: str) -> str:
    assert openai, "LLM not initialized"
    response = openai.chat.completions.create(
        model=model,
        messages=msgs2dicts(messages, openai=True),  # type: ignore
        temperature=1,
        top_p=1,
        presence_penalty=0,
        frequency_penalty=0
    )
    content = response.choices[0].message.content
    assert content
    return content

def stream(messages: list[Message], model: str) -> Generator[str, None, None]:
    assert openai, "LLM not initialized"
    stop_reason = None
    for chunk in openai.chat.completions.create(
        model=model,
        messages=msgs2dicts(messages, openai=True),  # type: ignore
        temperature=TEMPERATURE,
        top_p=TOP_P,
        stream=True,
        # the llama-cpp-python server needs this explicitly set, otherwise unreliable results
        # TODO: make this better
        max_tokens=1000 if not model.startswith("gpt-") else 4096,
    ):
        if not chunk.choices:  # type: ignore
            # Got a chunk with no choices, Azure always sends one of these at the start
            continue
        stop_reason = chunk.choices[0].finish_reason  # type: ignore
        content = chunk.choices[0].delta.content  # type: ignore
        if content:
            yield content
    logger.debug(f"Stop reason: {stop_reason}")