import io
import os
import click
import logging
from pathlib import Path
from contextlib import redirect_stdout

from ..llm import reply
from ..models import get_model
from ..tools import execute_msg
from ..prompts import get_prompt
from ..commands import execute_cmd
from ..init import init, init_logging
from ..message import print_msg, Message
from devopsx.cli import get_name, _conversations, LogManager, _include_paths

logger = logging.getLogger(__name__)


@click.command("dox")
@click.argument(
    "prompt",
    default=None,
    required=True,
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose output.")
@click.option(
    "--model",
    default=None,
    help="Model to use by default, can be overridden per request.",
)
@click.option(
    "--name",
    default="random",
    help="Name of the conversation to load. If no conversation exists, a new one will be created with a randomly generated name by default. Use 'ask' to be prompted for a name.",
)
def main(verbose: bool, model: str | None, name: str, prompt: str):  # pragma: no cover
    """
    Execute a command on the command line with a prompt and getting a response as stdout
    """

    init_logging(verbose)
    init(model, interactive=False, verbose=False)

    prev_conv_files = list(reversed(_conversations()))
    logdir = next((f.parent for f in prev_conv_files if f.parent.name == name), None)

    # print(*prev_conv_files, sep="\n")
    if not logdir:
        logdir = get_name(name)
        Path(logdir).mkdir(exist_ok=True)
        logfile = Path(logdir) / "conversation.jsonl"
        logfile.touch()
        log = LogManager.load(logfile)
    else:
        initial_msgs = [get_prompt("full")]
        logfile = Path(logdir) / "conversation.jsonl"
        log = LogManager.load(logfile, initial_msgs=initial_msgs, show_hidden=True)

    prompt_msg = Message("user", prompt.strip())
    msg = _include_paths(prompt_msg)
    log.append(msg, verbose=False)

    # if prompt is a user-command, execute it
    if log[-1].role == "user":
        # TODO: capture output of command and return it
        f = io.StringIO()
        with redirect_stdout(f):
            resp = execute_cmd(log[-1], log)
        if resp:
            log.write()
            output = f.getvalue()

    # performs reduction/context trimming, if necessary
    msgs = log.prepare_messages()

    # generate response
    # TODO: add support for streaming
    msg = reply(msgs, model=get_model().model, stream=False, verbose=False)
    msg.quiet = True

    # log response and run tools
    resp_msgs = []
    log.append(msg, verbose=False)
    resp_msgs.append(msg)
    for reply_msg in execute_msg(msg, ask=False):
        log.append(reply_msg, verbose=False)
        resp_msgs.append(reply_msg)

    for msg in resp_msgs:
        print_msg(Message(msg.role, msg.content))