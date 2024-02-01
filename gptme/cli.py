import errno
import importlib.metadata
import io
import logging
import os
import re
import readline  # noqa: F401
import sys
import urllib.parse
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Literal

import click
from pick import pick
from rich import print  # noqa: F401
from rich.console import Console

from .commands import CMDFIX, action_descriptions, execute_cmd
from .constants import MULTIPROMPT_SEPARATOR, PROMPT_USER
from .dirs import get_logs_dir
from .init import init, init_logging
from .llm import reply
from .logmanager import LogManager, _conversations
from .message import Message
from .prompts import get_prompt
from .tools import execute_msg
from .tools.shell import ShellSession, set_shell
from .util import epoch_to_age, generate_name

logger = logging.getLogger(__name__)
print_builtin = __builtins__["print"]  # type: ignore

LLMChoice = Literal["openai", "local"]
ModelChoice = Literal["gpt-3.5-turbo", "gpt-4", "gpt-4-1106-preview"]

script_path = Path(os.path.realpath(__file__))

docstring = """
GPTMe, a chat-CLI for LLMs, enabling them to execute commands and code.

If PROMPTS are provided, a new conversation will be started with it.
If one of the PROMPTS is 'MULTIPROMPT_SEPARATOR', following prompts will run after the assistant is done answering the first one.
The chat offers some commands that can be used to interact with the system:
""" + "\n".join(
    f"  {CMDFIX}{cmd:11s}  {desc}." for cmd, desc in action_descriptions.items()
)


@click.command(help=docstring)
@click.argument("prompts", default=None, required=False, nargs=-1)
@click.option("--prompt-system", default="full", help="System prompt. Can be 'full', 'short', or something custom.")
@click.option(
    "--name",
    default="random",
    help="Name of conversation. Defaults to generating a random name. Pass 'ask' to be prompted for a name.",
)
@click.option("--llm", default="openai", help="LLM to use.", type=click.Choice(["openai", "azure", "local"]))
@click.option("--model", default="gpt-4", help="Model to use.")
@click.option("--stream/--no-stream", is_flag=True, default=True, help="Stream responses")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output.")
@click.option("-y", "--no-confirm", is_flag=True, help="Skips all confirmation prompts.")
@click.option(
    "--interactive/--non-interactive",
    "-i/-n",
    default=True,
    help="Choose interactive mode, or not. Non-interactive implies --no-confirm, and is used in testing.",
)
@click.option("--show-hidden", is_flag=True, help="Show hidden system messages.")
@click.option("--version", is_flag=True, help="Show version.")
def main(
    prompts: list[str],
    prompt_system: str,
    name: str,
    llm: LLMChoice,
    model: ModelChoice,
    stream: bool,
    verbose: bool,
    no_confirm: bool,
    interactive: bool,
    show_hidden: bool,
    version: bool,
):
    """Main entrypoint for the CLI."""
    try:
        if version:
            print_builtin(f"gptme {importlib.metadata.version('gptme-python')}")
            exit(0)

        if "PYTEST_CURRENT_TEST" in os.environ:
            interactive = False

        if not interactive:
            no_confirm = True

        if no_confirm:
            logger.warning("Skipping all confirmation prompts.")

        initial_msgs = [get_prompt(prompt_system)]

        if not sys.stdin.isatty():
            prompt_stdin = _read_stdin()
            if prompt_stdin:
                initial_msgs += [Message("system", f"```stdin\n{prompt_stdin}\n```")]

                sys.stdin.close()
                try:
                    sys.stdin = open("/dev/tty")
                except OSError:
                    logger.warning("Failed to switch to interactive mode, continuing in non-interactive mode")

        sep = "\n\n" + MULTIPROMPT_SEPARATOR
        prompts = [p.strip() for p in "\n\n".join(prompts).split(sep) if p]
        prompt_msgs = [Message("user", p) for p in prompts]

        chat(
            prompt_msgs,
            initial_msgs,
            name,
            llm,
            model,
            stream,
            no_confirm,
            interactive,
            show_hidden,
        )
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


def chat(
    prompt_msgs: list[Message],
    initial_msgs: list[Message],
    name: str,
    llm: str,
    model: str,
    stream: bool = True,
    no_confirm: bool = False,
    interactive: bool = True,
    show_hidden: bool = False,
):
    try:
        init(llm, model, interactive)
        set_shell(ShellSession())

        logfile = get_logfile(name, interactive=(not prompt_msgs and interactive) and sys.stdin.isatty())
        print(f"Using logdir {logfile.parent}")
        log = LogManager.load(logfile, initial_msgs=initial_msgs, show_hidden=show_hidden)
        log.print()
        print("--- ^^^ past messages ^^^ ---")

        while True:
            if prompt_msgs:
                msg = prompt_msgs.pop(0)
                msg = _include_paths(msg)
                log.append(msg)
                if execute_cmd(msg, log):
                    continue
            elif not interactive:
                from .tools import is_supported_codeblock

                codeblock = log.get_last_code_block("assistant", history=1, content=False)
                if not (codeblock and is_supported_codeblock(codeblock)):
                    logger.info("Non-interactive and exhausted prompts, exiting")
                    exit(0)

            for msg in loop(log, no_confirm, model, stream=stream):
                log.append(msg)
                if msg.role == "user" and execute_cmd(msg, log):
                    break
    except Exception as e:
        logger.error(f"An error occurred in chat function: {e}")
        sys.exit(1)


def loop(
    log: LogManager,
    no_confirm: bool,
    model: str,
    stream: bool = True,
) -> Generator[Message, None, None]:
    try:
        last_msg = log[-1] if log else None
        if not last_msg or (last_msg.role in ["assistant"]) or last_msg.content == "Interrupted" or last_msg.pinned:
            inquiry = prompt_user()
            if not inquiry:
                print()
                return
            msg = Message("user", inquiry, quiet=True)
            msg = _include_paths(msg)
            yield msg

        try:
            msgs = log.prepare_messages()
            for m in msgs:
                logger.debug(f"Prepared message: {m}")

            msg_response = reply(msgs, model, stream)
            if msg_response:
                msg_response.quiet = True
                yield msg_response
                yield from execute_msg(msg_response, ask=not no_confirm)
        except KeyboardInterrupt:
            yield Message("system", "Interrupted")
    except Exception as e:
        logger.error(f"An error occurred in loop function: {e}")
        sys.exit(1)


def get_logfile(name: str, interactive=True) -> Path:
    try:
        title = "New conversation or load previous? "
        NEW_CONV = "New conversation"
        prev_conv_files = list(reversed(_conversations()))

        def is_test(name: str) -> bool:
            return "-test-" in name or name.startswith("test-")

        if interactive:
            options = [
                NEW_CONV,
            ] + prev_convs

            index: int
            _, index = pick(options, title)
            if index == 0:
                logdir = get_name(name)
            else:
                logdir = get_logs_dir() / prev_conv_files[index - 1].parent
        else:
            logdir = get_name(name)

        if not os.path.exists(logdir):
            os.mkdir(logdir)
        logfile = logdir / "conversation.jsonl"
        if not os.path.exists(logfile):
            open(logfile, "w").close()
        return logfile
    except Exception as e:
        logger.error(f"An error occurred in get_logfile function: {e}")
        sys.exit(1)


def prompt_user(value=None) -> str:
    try:
        response = prompt_input(PROMPT_USER, value)
        if response:
            readline.add_history(response)
        return response
    except Exception as e:
        logger.error(f"An error occurred in prompt_user function: {e}")
        sys.exit(1)


def prompt_input(prompt: str, value=None) -> str:
    try:
        prompt = prompt.strip() + ": "
        if value:
            print(prompt + value)
        else:
            prompt = _rich_to_str(prompt)
            original_stdout = sys.stdout
            sys.stdout = sys.__stdout__
            value = input(prompt.strip() + " ")
            sys.stdout = original_stdout
        return value
    except Exception as e:
        logger.error(f"An error occurred in prompt_input function: {e}")
        sys.exit(1)


def _rich_to_str(s: str) -> str:
    try:
        console = Console(file=io.StringIO(), color_system="256")
        console.print(s)
        return console.file.getvalue()
    except Exception as e:
        logger.error(f"An error occurred in _rich_to_str function: {e}")
        sys.exit(1)


def _read_stdin() -> str:
    try:
        chunk_size = 1024
        all_data = ""
        while True:
            chunk = sys.stdin.read(chunk_size)
            if not chunk:
                break
            all_data += chunk
        return all_data
    except Exception as e:
        logger.error(f"An error occurred in _read_stdin function: {e}")
        sys.exit(1)


def _include_paths(msg: Message) -> Message:
    try:
        assert msg.role == "user"
        cwd_files = [f.name for f in Path.cwd().iterdir()]
        content_no_codeblocks = re.sub(r"```.*?\n```", "", msg.content, flags=re.DOTALL)
        append_msg = ""
        for word in re.split(r"[\s`]", content_no_codeblocks):
            word = word.strip("`")
            word = word.rstrip("?")
            if not word:
                continue
            if (
                any(word.startswith(s) for s in ["/", "~/", "./"])
                or word.startswith("http")
                or any(word.split("/", 1)[0] == file for file in cwd_files)
            ):
                logger.debug(f"potential path/url: {word=}")
                p = _parse_prompt(word)
                if p:
                    append_msg += "\n\n" + p

        if append_msg:
            msg.content += append_msg

        return msg
    except Exception as e:
        logger.error(f"An error occurred in _include_paths function: {e}")
        sys.exit(1)


def _parse_prompt(prompt: str) -> str | None:
    try:
        if any(prompt.startswith(command) for command in [f"{CMDFIX}{cmd}" for cmd in action_descriptions.keys()]):
            return None

        words = prompt.split()
        paths = []
        urls = []
        for word in words:
            f = Path(word).expanduser()
            if f.exists() and f.is_file():
                paths.append(word)
                continue
            try:
                p = urllib.parse.urlparse(word)
                if p.scheme and p.netloc:
                    urls.append(word)
            except ValueError:
                pass

        result = ""
        if paths or urls:
            result += "\n\n"
            if paths:
                logger.debug(f"{paths=}")
            if urls:
                logger.debug(f"{urls=}")
        for path in paths:
            result += _parse_prompt(path) or ""

        for url in urls:
            try:
                from .tools.browser import read_url
            except ImportError:
                logger.warning(
                    "Failed to import browser tool, skipping URL expansion." "You might have to install browser extras."
                )
                continue

            try:
                content = read_url(url)
                result += f"```{url}\n{content}\n```"
            except Exception as e:
                logger.warning(f"Failed to read URL {url}: {e}")

        return result
    except Exception as e:
        logger.error(f"An error occurred in _parse_prompt function: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
