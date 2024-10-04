import sys
import shutil
import logging
from rich import print
from typing import Literal
from functools import lru_cache
from collections.abc import Iterator

from .tools import ToolUse
from .config import get_config
from .constants import PROMPT_ASSISTANT
from .message import Message, len_tokens, format_msgs
from .models import MODELS, get_summary_model

from .llm_anthropic import chat as chat_anthropic
from .llm_anthropic import get_client as get_anthropic_client
from .llm_anthropic import init as init_anthropic
from .llm_anthropic import stream as stream_anthropic

from .llm_openai import chat as chat_openai
from .llm_openai import reasoning_chat as reasoning_chat_openai
from .llm_openai import get_client as get_openai_client
from .llm_openai import init as init_openai
from .llm_openai import stream as stream_openai

from .llm_groq import chat as chat_groq
from .llm_groq import get_client as get_groq_client
from .llm_groq import init as init_groq
from .llm_groq import stream as stream_groq

from .llm_ollama import chat as chat_ollama
from .llm_ollama import get_client as get_ollama_client
from .llm_ollama import init as init_ollama
from .llm_ollama import stream as stream_ollama


logger = logging.getLogger(__name__)

Provider = Literal["openai", "azure", "openrouter", "local", "anthropic", "groq"]

def init_llm(llm: str):
    # set up API_KEY (if openai) and API_BASE (if local)
    config = get_config()

    if llm in ["openai", "azure", "openrouter"]:
        init_openai(llm, config)
        assert get_openai_client()
    elif llm == "anthropic":
        init_anthropic(config)
        assert get_anthropic_client()
    elif llm == "groq":
        init_groq(config)
        assert get_groq_client()
    elif llm == "local":
        init_ollama(config)
        assert get_ollama_client()
    else:
        print(f"Error: Unknown LLM: {llm}")
        sys.exit(1)


def reply(messages: list[Message], model: str, stream: bool = False, verbose: bool = True) -> Message:
    if stream:
        return _reply_stream(messages, model)
    else:
        if verbose: print(f"{PROMPT_ASSISTANT}: Thinking...", end="\r")
        response = _chat_complete(messages, model)
        if verbose: print(" " * shutil.get_terminal_size().columns, end="\r")
        if verbose: print(f"{PROMPT_ASSISTANT}: {response}")
        return Message("assistant", response)


def _chat_complete(messages: list[Message], model: str) -> str:
    provider = _client_to_provider()
    if provider in ["openai", "azure", "openrouter"]:
        return reasoning_chat_openai(messages, model) if model.startswith("o1-") else chat_openai(messages, model)
    elif provider == "anthropic":
        return chat_anthropic(messages, model)
    elif provider == "groq":
        return chat_groq(messages, model)
    elif provider == "local":
        return chat_ollama(messages, model)
    else:
        raise ValueError("LLM not initialized")


def _stream(messages: list[Message], model: str) -> Iterator[str]:
    provider = _client_to_provider()
    if provider in ["openai", "azure", "openrouter"]:
        return stream_openai(messages, model)
    elif provider == "anthropic":
        return stream_anthropic(messages, model)
    elif provider == "groq":
        return stream_groq(messages, model)
    elif provider == "local":
        return stream_ollama(messages, model)
    else:
        raise ValueError("LLM not initialized")


def _reply_stream(messages: list[Message], model: str) -> Message:
    print(f"{PROMPT_ASSISTANT}: Thinking...", end="\r")

    def print_clear():
        print(" " * shutil.get_terminal_size().columns, end="\r")

    output = ""
    try:
        for char in (char for chunk in _stream(messages, model) for char in chunk):
            if not output:  # first character
                print_clear()
                print(f"{PROMPT_ASSISTANT}: ", end="")
                
            print(char, end="")
            assert len(char) == 1
            output += char

            # need to flush stdout to get the print to show up
            sys.stdout.flush()

            # pause inference on finished code-block, letting user run the command before continuing
            tooluses = list(ToolUse.iter_from_content(output))
            if tooluses and any(tooluse.is_runnable for tooluse in tooluses):
                logger.warning("Found tool use, breaking")
                break
    except KeyboardInterrupt:
        return Message("assistant", output + "... ^C Interrupted")
    finally:
        print_clear()
    return Message("assistant", output)


def _client_to_provider() -> Provider:
    openai_client = get_openai_client()
    anthropic_client = get_anthropic_client()
    groq_client = get_groq_client()
    ollama_client = get_ollama_client()
    assert any([openai_client, anthropic_client, groq_client, ollama_client]), "No client initialized"
    if openai_client:
        if "openai" in openai_client.base_url.host:
            return "openai"
        elif "openrouter" in openai_client.base_url.host:
            return "openrouter"
        else:
            return "azure"
    elif anthropic_client:
        return "anthropic"
    elif groq_client:
        return "groq"
    elif ollama_client:
        return "local"
    else:
        raise ValueError("Unknown client type")


def weaviate_summarize(content: str) -> str:
    """
    Summarizes a conversation log using `claude-3-5-sonnet-20240620` model
    """
    messages = [
        Message(
            "system",
            content="""
You have a comprehensive conversation log consisting of Linux commands and code blocks (Python, shell scripts, JavaScript, etc.) along with their execution results. Your objective is to create a structured summary that captures the logical progression of the conversation. Focus on the following elements:

1. Introduction and Context: Begin by summarizing the initial setup or context of the conversation. Identify the primary goal or problem being addressed.
2. Logical Steps and Commands: Break down the conversation into a sequence of logical steps, outlining the key commands and code blocks used at each stage. For each step, specify:
    - The command or code blocks executed
        * Capture the command and code block to ensure they can be easily referenced in the future.
        * For code blocks exceeding 50 lines, truncate it to the first and last 20 lines, keeping the rest as ["...Truncated Output..."]. 
    - The purpose of executing this step and any relevant parameters.
3. Execute Results and Analysis: For each logical step, summarize the execution results, noting:
    - Successes and any changes made to the system.
    - Errors or unexpected outcomes, including error messages if applicable.
    - Analysis or interpretation of the results and any conclusions drawn.
4. Troubleshooting and Problem-Solving: Highlight any troubleshooting steps taken to resolve issues, including alternative commands or methods tested.
5. Final Outcomes and Decisions: Conclude with a summary of the final outcomes, any decisions made, and their rationale. Include any insights gained that are relevant for future tasks.
            """,
        ),
        Message("user", content=f"Summarize this:\n{content}"),
    ]

    model = "claude-3-5-sonnet-20240620"
    context_limit = MODELS["anthropic"]["claude-3-5-sonnet-20240620"]["context"]
    if len_tokens(messages) > context_limit:
        raise ValueError(
            f"Cannot summarize more than {context_limit} tokens, got {len_tokens(messages)}"
        )

    summary = _chat_complete(messages, model)
    assert summary
    logger.debug(
        f"Summarized current conversation ({len_tokens(content)} -> {len_tokens(summary)} tokens): "
        + summary
    )
    return summary


def _summarize_str(content: str) -> str:
    """
    Summarizes a long text using a LLM.

    To summarize messages or the conversation log,
    use `devopsx.tools.summarize` instead (which wraps this).
    """
    messages = [
        Message(
            "system",
            content="You are a helpful assistant that helps summarize messages with an AI assistant through a tool called devopsx.",
        ),
        Message("user", content=f"Summarize this:\n{content}"),
    ]

    provider = _client_to_provider()
    model = get_summary_model(provider)
    context_limit = MODELS[provider][model]["context"]
    if len_tokens(messages) > context_limit:
        raise ValueError(
            f"Cannot summarize more than {context_limit} tokens, got {len_tokens(messages)}"
        )

    summary = _chat_complete(messages, model)
    assert summary
    logger.debug(
        f"Summarized long output ({len_tokens(content)} -> {len_tokens(summary)} tokens): "
        + summary
    )
    return summary


def generate_name(msgs: list[Message]) -> str:
    """
    Generates a name for a given text/conversation using a LLM.
    """
    # filter out system messages
    msgs = [m for m in msgs if m.role != "system"]
    msgs = (
        [
            Message(
                "system",
                """
The following is a conversation between a user and an assistant. Which we will generate a name for.

The name should be 3-6 words describing the conversation, separated by dashes. Examples:
 - install-llama
 - implement-game-of-life
 - capitalize-words-in-python

Focus on the main and/or initial topic of the conversation. Avoid using names that are too generic or too specific.

IMPORTANT: output only the name, no preamble or postamble.
""",
            )
        ]
        + msgs
        + [Message("user", "Now, generate a name for this conversation.")]
    )
    name = _chat_complete(msgs, model=get_summary_model(_client_to_provider())).strip()
    return name


def summarize(msg: str | Message | list[Message]) -> Message:
    """Uses a cheap LLM to summarize long outputs."""
    # construct plaintext from message(s)
    if isinstance(msg, str):
        content = msg
    elif isinstance(msg, Message):
        content = msg.content
    else:
        content = "\n".join(format_msgs(msg))

    logger.info(f"{content[:200]=}")
    summary = _summarize_helper(content)
    logger.info(f"{summary[:200]=}")

    # construct message from summary
    content = f"Here's a summary of the conversation:\n{summary}"
    return Message(role="system", content=content)


@lru_cache(maxsize=128)
def _summarize_helper(s: str, tok_max_start=400, tok_max_end=400) -> str:
    """
    Helper function for summarizing long outputs.
    Truncates long outputs, then summarizes.
    """
    if len_tokens(s) > tok_max_start + tok_max_end:
        beginning = " ".join(s.split()[:tok_max_start])
        end = " ".join(s.split()[-tok_max_end:])
        summary = _summarize_str(beginning + "\n...\n" + end)
    else:
        summary = _summarize_str(s)
    return summary