import logging
import re
import sys
from collections.abc import Generator
from pathlib import Path
from time import sleep
from typing import Literal

from . import llm
from .constants import CMDFIX
from .logmanager import LogManager
from .message import Message, msgs_to_toml, print_msg, toml_to_msgs
from .tools import execute_msg, execute_python, execute_shell
from .tools.context import gen_context_msg
from .tools.summarize import summarize
from .tools.useredit import edit_text_with_editor
from .util import ask_execute, len_tokens
from .ssh import interactive_ssh_session

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
    "python",
    "replay",
    "undo",
    "impersonate",
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
    "shell": "Execute shell code",
    "python": "Execute Python code",
    "replay": "Re-execute codeblocks in the conversation, wont store output in log",
    "impersonate": "Impersonate the assistant",
    "tokens": "Show the number of tokens used",
    "help": "Show this help message",
    "exit": "Exit the program",
}

COMMANDS = set(action_descriptions.keys())

def execute_cmd(msg: Message, log: LogManager) -> bool:
    """Executes any user-command, returns True if command was executed."""
    assert msg.role == "user"

    # if message starts with ., treat as command
    # when command has been run,
    if msg.content.startswith("/"):
        for resp in handle_cmd(msg.content, log, no_confirm=True):
            log.append(resp)
        return True
    elif msg.content.startswith("ssh "):
        try:
            parts = msg.split()
            if len(parts) >= 4:
                hostname, username, port = parts[1:4]
                port = int(port)
                interactive_ssh_session(hostname, port, username)
            print("SSH session ended. Returning to gptme.")
        except Exception as e:
            print(f"Error during SSH session: {e}")
    return False

def handle_cmd(
    cmd: str, log: LogManager, no_confirm: bool
) -> Generator[Message, None, None]:
    """Handles a command."""
    cmd = cmd.lstrip(CMDFIX)
    logger.debug(f"Executing command: {cmd}")
    name, *args = re.split(r"[\n\s]", cmd)
    full_args = cmd.split(" ", 1)[1] if " " in cmd else ""

    command_handlers = {
        "bash": execute_shell,
        "sh": execute_shell,
        "shell": execute_shell,
        "python": execute_python,
        "py": execute_python,
        "log": lambda: (log.undo(1, quiet=True), log.print(show_hidden="--hidden" in args)),
        "rename": lambda: (log.undo(1, quiet=True), log.write(), rename(log, args[0] if args else input("New name: "), ask=not no_confirm)),
        "fork": lambda: log.fork(args[0] if args else input("New name: ")),
        "summarize": lambda: summarize_and_print(log),
        "edit": lambda: (log.undo(1, quiet=True), edit(log)),
        "context": lambda: yield gen_context_msg(),
        "undo": lambda: (log.undo(1, quiet=True), log.undo(int(args[0]) if args and args[0].isdigit() else 1)),
        "save": lambda: (log.undo(1, quiet=True), save(log, args[0] if args else input("Filename: "))),
        "exit": sys.exit,
        "replay": lambda: (log.undo(1, quiet=True), log.write(), replay(log)),
        "impersonate": lambda: impersonate(log, full_args, no_confirm),
        "tokens": lambda: (log.undo(1, quiet=True), print(f"Tokens used: {len_tokens(log.log)}")),
        "_default": lambda: (log.undo(1, quiet=True), log.write(), help())
    }

    handler = command_handlers.get(name, command_handlers["_default"])
    try:
        yield from handler()
    except Exception as e:
        print(f"Error executing command '{name}': {e}")

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
    print(f"Summary: {summary}")

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
    code = log.get_last_code_block(content=True)
    if not code:
        print("No code block found")
        return
    if Path(filename).is_file():
        confirm = ask_execute("File already exists, overwrite?", default=False)
        if not confirm:
            return
    try:
        with open(filename, "w") as f:
            f.write(code)
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
