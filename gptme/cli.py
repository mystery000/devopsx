import errno
import importlib.metadata
import io
import logging
import os
import re
import sys
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Literal

import click
from pick import pick
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

try:
    from .tools.browser import read_url
except ImportError:
    read_url = None


def read_stdin() -> str:
    try:
        return sys.stdin.read()
    except KeyboardInterrupt:
        return ""


def rich_to_str(s: str) -> str:
    console = Console(file=io.StringIO(), color_system="256")
    console.print(s)
    return console.file.getvalue()


def include_paths(msg: Message) -> Message:
    assert msg.role == "user"

    cwd_files = {f.name for f in Path.cwd().iterdir()}
    content_no_codeblocks = re.sub(r"```.*?\n```", "", msg.content, flags=re.DOTALL)
    append_msg = ""

    for word in re.split(r"[\s`]", content_no_codeblocks):
        word = word.strip("`").rstrip("?")
        if not word:
            continue

        if (
            word.startswith("/") or word.startswith("~/") or word.startswith("./")
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


def parse_prompt(prompt: str) -> str or None:
    if any(prompt.startswith(f"{CMDFIX}{cmd}") for cmd in action_descriptions.keys()):
        return None

    try:
        f = Path(prompt).expanduser()
        if f.exists() and f.is_file():
            return f"```{prompt}\n{Path(prompt).expanduser().read_text()}\n```"
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Error reading file: {e}")

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

    for path in paths:
        result += parse_prompt(path) or ""

    for url in urls:
        lazy_import_browser()
        if read_url:
            try:
                content = read_url(url)
                result += f"```{url}\n{content}\n```"
            except Exception as e:
                logger.warning(f"Failed to read URL {url}: {e}")

    return result


def lazy_import_browser():
    global read_url
    if read_url is None:
        from .tools.browser import read_url as imported_read_url
        read_url = imported_read_url


def get_logfile(name: str, interactive=True) -> Path:
    title = "New conversation or load previous? "
    NEW_CONV = "New conversation"
    prev_conv_files = list(reversed(_conversations()))

    def is_test(name: str) -> bool:
        return "-test-" in name or name.startswith("test-")

    if interactive:
        options = [NEW_CONV] + [
            f"{f.parent.name:30s} \t{epoch_to_age(f.stat().st_mtime)} \t{len(f.read_text().splitlines()):5d} msgs"
            for f in prev_conv_files
        ]
        _, index = pick(options, title)
        if index == 0:
            logdir = get_name(name)
        else:
            logdir = get_logs_dir() / prev_conv_files[index - 1].parent
    else:
        logdir = get_name(name)

    if not os.path.exists(logdir):
        try:
            os.mkdir(logdir)
        except OSError as e:
            logger.error(f"Error creating directory {logdir}: {e}")

    logfile = logdir / "conversation.jsonl"
    if not os.path.exists(logfile):
        try:
            open(logfile, "w").close()
        except OSError as e:
            logger.error(f"Error creating file {logfile}: {e}")

    return logfile


def get_name(name: str) -> Path:
    datestr = datetime.now().strftime("%Y-%m-%d")
    logsdir = get_logs_dir()

    if name == "random":
        for _ in range(3):
            name = generate_name()
            logpath = logsdir / f"{datestr}-{name}"
            if not logpath.exists():
                break
        else:
            raise ValueError("Failed to generate unique name")
    elif name == "ask":
        while True:
            name = input("Name for conversation (or empty for random words): ")
            name = f"{datestr}-{name}"
            logpath = logsdir / name

            if not logpath.exists():
                break
            else:
                print(f"Name {name} already exists, try again.")
    else:
        try:
            datetime.strptime(name[:10], "%Y-%m-%d")
        except ValueError:
            name = f"{datestr}-{name}"
        logpath = logsdir / name

    return logpath


def prompt_user(value=None) -> str:
    try:
        response = prompt_input(PROMPT_USER, value)
        if response:
            readline.add_history(response)
        return response
    except KeyboardInterrupt:
        return ""


def prompt_input(prompt: str, value=None) -> str:
    prompt = prompt.strip() + ": "
    if value:
        print(prompt + value)
    else:
        prompt = rich_to_str(prompt)
        original_stdout = sys.stdout
        sys.stdout = sys.__stdout__
        try:
            value = input(prompt.strip() + " ")
        except KeyboardInterrupt:
            value = ""
        finally:
            sys.stdout = original_stdout

    return value


def main():
    try:
        interactive = True
        version = False
        if len(sys.argv) > 1 and sys.argv[1] == "--version":
            version = True
        elif len(sys.argv) > 1 and sys.argv[1] == "--non-interactive":
            interactive = False

        if version:
            print_builtin(f"gptme {importlib.metadata.version('gptme-python')}")
            sys.exit(0)

        if "PYTEST_CURRENT_TEST" in os.environ:
            interactive = False

        init_logging(interactive)

        if not interactive:
            logger.warning("Skipping all confirmation prompts.")

        no_confirm = "--no-confirm" in sys.argv

        initial_msgs = [get_prompt("full")]

        if not sys.stdin.isatty():
            prompt_stdin = read_stdin()
            if prompt_stdin:
                initial_msgs.append(Message("system", f"```stdin\n{prompt_stdin}\n```"))
                sys.stdin.close()
                try:
                    sys.stdin = open("/dev/tty")
                except OSError:
                    logger.warning("Failed to switch to interactive mode, continuing in non-interactive mode")

        sep = "\n\n" + MULTIPROMPT_SEPARATOR
        prompts = [p.strip() for p in "\n\n".join(sys.argv[1:]).split(sep) if p]
        prompt_msgs = [Message("user", p) for p in prompts]

        chat(prompt_msgs, initial_msgs, interactive, no_confirm)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


def chat(prompt_msgs: list[Message], initial_msgs: list[Message], interactive: bool, no_confirm: bool):
    init(interactive)
    set_shell(ShellSession())
    logfile = get_logfile("", interactive=(not prompt_msgs and interactive) and sys.stdin.isatty())
    print(f"Using logdir {logfile.parent}")

    try:
        log = LogManager.load(logfile, initial_msgs=initial_msgs, show_hidden=False)
        log.print()
        print("--- ^^^ past messages ^^^ ---")

        while True:
            if prompt_msgs:
                msg = prompt_msgs.pop(0)
                msg = include_paths(msg)
                log.append(msg)

                if execute_cmd(msg, log):
                    continue
            elif not interactive:
                codeblock = log.get_last_code_block("assistant", history=1, content=False)
                if not (codeblock and is_supported_codeblock(codeblock)):
                    logger.info("Non-interactive and exhausted prompts, exiting")
                    sys.exit(0)

            inquiry = prompt_user()
            if not inquiry:
                print()
                return

            msg = Message("user", inquiry, quiet=True)
            msg = include_paths(msg)
            log.append(msg)

            for m in loop(log, no_confirm):
                log.append(m)
                if m.role == "user" and execute_cmd(m, log):
                    break

    except KeyboardInterrupt:
        print("Interrupted.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


def loop(log: LogManager, no_confirm: bool) -> Generator[Message, None, None]:
    last_msg = log[-1] if log else None

    if not last_msg or last_msg.role in ["assistant"] or last_msg.content == "Interrupted" or last_msg.pinned:
        inquiry = prompt_user()
        if not inquiry:
            print()
            return
        msg = Message("user", inquiry, quiet=True)
        msg = include_paths(msg)
        yield msg

    try:
        msgs = log.prepare_messages()

        for m in msgs:
            logger.debug(f"Prepared message: {m}")

        msg_response = reply(msgs, "", stream=True)

        if msg_response:
            msg_response.quiet = True
            yield msg_response
            yield from execute_msg(msg_response, ask=not no_confirm)

    except KeyboardInterrupt:
        yield Message("system", "Interrupted")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main()
