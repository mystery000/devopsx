import re
import sys
import rich
import logging
from time import sleep
from pathlib import Path
from typing import Literal
from tabulate import tabulate
from collections.abc import Generator

from . import llm
from .constants import CMDFIX
from .logmanager import LogManager
from .message import Message, msgs_to_toml, print_msg, toml_to_msgs, len_tokens
from .tools.context import gen_context_msg
from .tools.summarize import summarize
from .tools.useredit import edit_text_with_editor
from .util import ask_execute
from .tools import execute_msg, execute_python, execute_shell, execute_subagent, loaded_tools
from .models import MODELS, get_model

logger = logging.getLogger(__name__)

Actions = Literal[
    "summarize",
    "log",
    "edit",
    "rename",
    "fork",
    "summarize",
    "context",
    "save",
    "shell",
    "subagent",
    "python",
    "replay",
    "undo",
    "impersonate",
    "tools",
    "models",
    "tokens",
    "help",
    "exit",
]

action_descriptions: dict[Actions, str] = {
    "undo": "Undo the last action",
    "log": "Show the conversation log",
    "edit": "Edit the conversation in your editor",
    "rename": "Rename the conversation",
    "fork": "Create a copy of the conversation with a new name",
    "summarize": "Summarize the conversation",
    "save": "Save the last code block to a file",
    "shell": "Execute shell commands",
    "subagent": "Manage subagents",
    "python": "Execute Python code",
    "replay": "Re-execute codeblocks in the conversation, wont store output in log",
    "impersonate": "Impersonate the assistant",
    "tokens": "Show the number of tokens used",
    "tools": "Show available tools",
    "models": "Show available models",
    "help": "Show this help message",
    "exit": "Exit the program",
}

COMMANDS = set(action_descriptions.keys())

def execute_cmd(msg: Message, log: LogManager, pty: bool = True) -> bool:
    """Executes any user-command, returns True if command was executed."""
    assert msg.role == "user"

    # if message starts with ., treat as command
    # when command has been run,
    if msg.content[:1] in ["/"]:
        for resp in handle_cmd(msg.content, log, no_confirm=True, pty=pty):
            log.append(resp)
        return True
    return False

def handle_cmd(
    cmd: str, log: LogManager, no_confirm: bool, pty: bool
) -> Generator[Message, None, None]:
    """Handles a command."""
    cmd = cmd.lstrip(CMDFIX)
    logger.debug(f"Executing command: {cmd}")
    name, *args = re.split(r"[\n\s]", cmd)
    full_args = cmd.split(" ", 1)[1] if " " in cmd else ""
    match name:
        # TODO: rewrite to auto-register tools using block_types
        case "subagent":
            yield from execute_subagent(full_args, ask=not no_confirm, args=[])
        case "bash" | "sh" | "shell":
            yield from execute_shell(full_args, ask=not no_confirm, args=[])
        case "python" | "py":
            yield from execute_python(full_args, ask=not no_confirm, args=[])
        case "log":
            log.undo(1, quiet=True)
            log.print(show_hidden="--hidden" in args)
        case "rename":
            log.undo(1, quiet=True)
            log.write()
            # rename the conversation
            print("Renaming conversation (enter empty name to auto-generate)")
            new_name = args[0] if args else input("New name: ")
            rename(log, new_name, ask=not no_confirm)
        case "fork":
            # fork the conversation
            new_name = args[0] if args else input("New name: ")
            log.fork(new_name)
        case "summarize":
            summarize_and_print(log)
        case "edit":
            # edit previous messages
            # first undo the '/edit' command itself
            log.undo(1, quiet=True)
            yield from edit(log)
        case "context":
            # print context msg
            yield gen_context_msg()
        case "undo":
            # undo the '/undo' command itself
            log.undo(1, quiet=True)
            # if int, undo n messages
            n = int(args[0]) if args and args[0].isdigit() else 1
            log.undo(n)
        case "save":
            # undo
            log.undo(1, quiet=True)
            filename = args[0] if args else input("Filename: ")
            save(log, filename)
        case "exit":
            sys.exit(0)
        case "replay":
            log.undo(1, quiet=True)
            log.write()
            print("Replaying conversation...")
            for msg in log.log:
                if msg.role == "assistant":
                    for reply_msg in execute_msg(msg, ask=True):
                        print_msg(reply_msg, oneline=False)
        case "impersonate":
            content = full_args if full_args else input("[impersonate] Assistant: ")
            msg = Message("assistant", content)
            yield msg
            yield from execute_msg(msg, ask=not no_confirm)
        case "tokens":
            log.undo(1, quiet=True)
            print(f"Tokens used: {len_tokens(log.log)}")
        case "tools":
            log.undo(1, quiet=True)
            print("Available tools:")
            for tool in loaded_tools:
                rich.print(
                    f"""
- [blue]{tool.name}[/blue]  ({tool.desc.rstrip(".")})
    tokens (example): {len_tokens(tool.examples)}
                      """.strip()
                )
        case "models":
            log.undo(1, quiet=True)
            model = get_model()
            print(f"Selected model: {model.provider}/{model.model}")
            print("Available models:")
            for provider in MODELS:
                for model, details in MODELS[provider].items():
                    rich.print(
                        f"""
- [blue]{model}[/blue] (provider: [cyan]{provider}[/cyan], context window: {details["context"]})
                    """.strip()
                    )
        case _:
            if log.log[-1].content != f"{CMDFIX}help":
                print("Unknown command")
            # undo the '/help' command itself
            log.undo(1, quiet=True)
            log.write()
            help()

def edit(log: LogManager) -> Generator[Message, None, None]:  # pragma: no cover
    # generate editable toml of all messages
    t = msgs_to_toml(reversed(log.log))  # type: ignore
    res = None
    while not res:
        try:
            t = edit_text_with_editor(t, "toml")
            res = toml_to_msgs(t)
        except Exception as e:
            print(f"\nFailed to parse TOML: {e}")
            try:
                sleep(1)
            except KeyboardInterrupt:
                yield Message("system", "Interrupted")
                return
    log.edit(list(reversed(res)))
    # now we need to redraw the log so the user isn't seeing stale messages in their buffer
    # log.print()
    print("Applied edited messages, write /log to see the result")

def summarize_and_print(log: LogManager):
    msgs = log.prepare_messages()
    msgs = [m for m in msgs if not m.hide]
    summary = summarize(msgs)
    print_msg(summary)

def replay(log: LogManager):
    print("Replaying conversation...")
    for msg in log.log:
        if msg.role == "assistant":
            try:
                for msg in execute_msg(msg, ask=True):
                    print_msg(msg, oneline=False)
            except Exception as e:
                print(f"Error during replay: {e}")

def impersonate(log: LogManager, full_args: str, no_confirm: bool):
    content = full_args if full_args else input("[impersonate] Assistant: ")
    msg = Message("assistant", content)
    try:
        yield msg
        yield from execute_msg(msg, ask=not no_confirm)
    except Exception as e:
        print(f"Error during impersonation: {e}")

def save(log: LogManager, filename: str):
    # save the most recent code block to a file
    codeblock = log.get_last_code_block()
    if not codeblock:
        print("No code block found")
        return
    _, content = codeblock
    if Path(filename).is_file():
        confirm = ask_execute("File already exists, overwrite?", default=False)
        if not confirm:
            return
    try:
        with open(filename, "w") as f:
            f.write(content)
        print(f"Saved code block to {filename}")
    except Exception as e:
        print(f"Error saving code block: {e}")

def rename(log: LogManager, new_name: str, ask: bool = True):
    try:
        if new_name in ["", "auto"]:
            new_name = llm.generate_name(log.prepare_messages())
            assert " " not in new_name
            print(f"Generated name: {new_name}")
            if ask:
                confirm = ask_execute("Confirm?")
                if not confirm:
                    print("Aborting")
                    return
            log.rename(new_name, keep_date=True)
        else:
            log.rename(new_name, keep_date=False)
        print(f"Renamed conversation to {log.logfile.parent}")
    except Exception as e:
        print(f"Error during conversation renaming: {e}")

def help():
    longest_cmd = max(len(cmd) for cmd in COMMANDS)
    print("Available commands:")
    for cmd, desc in action_descriptions.items():
        print(f"  /{cmd.ljust(longest_cmd)}  {desc}")
