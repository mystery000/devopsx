import sys
import tty
import time
import click
import select
import logging
import paramiko
from collections.abc import Generator
from ..message import Message, print_msg
from ..util import ask_execute, print_preview
from .shell import _shorten_stdout, _format_block_smart

logger = logging.getLogger(__name__)

class PseudoShell:
    "A wrapper of paramiko.SSHClient"
    TIMEOUT = 4

    def __init__(self, hostname, port, username, password, look_for_keys=False):
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname, port, username=username, password=password, timeout=self.TIMEOUT, look_for_keys=look_for_keys)

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def run(self, command, sudo=False) -> tuple[int, str, str]:
        feed_password = False
        if sudo and self.username != "root":
            command = "sudo -S -p '' %s" % command
            feed_password = self.password is not None and len(self.password) > 0

        stdin, stdout, stderr = self.client.exec_command(command)

        if feed_password:
            stdin.write(self.password + "\n")
            stdin.flush()
        
        return (
            stdout.channel.recv_exit_status(),
            "".join(stdout.readlines()).strip(),
            "".join(stderr.readlines()).strip()
        )
 
_pseudo_shells = dict()

def get_shell(hostname: str, port: int, username: str, password: str) -> PseudoShell:
    global _pseudo_shells
    shell_id = hostname.replace(".", "")
    if f"{shell_id}" not in _pseudo_shells:
        _pseudo_shells[f"{shell_id}"] = PseudoShell(hostname, port, username, password)
    return _pseudo_shells[f"{shell_id}"]

def execute_pseudo_shell(cmd: str, ask=True)-> Generator[Message, None, None]:
    pseudo_shell = get_shell(hostname="213.156.159.139", port=22, username="devopsx", password="devopsx")
    try:
        return_code, stdout, stderr = pseudo_shell.run(cmd, sudo=True)
        msg = _format_block_smart("Ran command", cmd, lang="bash") + "\n\n"
        if stdout:
            msg += _format_block_smart("stdout", stdout) + "\n\n"
        if stderr:
            msg += _format_block_smart("stderr", stderr) + "\n\n"
        if not stdout and not stderr:
            msg += "No output\n"
        yield Message("system", msg)
    except Exception as e:
        yield Message(
            "system",
            content=f"An error occurred: {e}",
        )