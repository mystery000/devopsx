"""
A subthread tool for devopsx

Lets devopsx break down a task into smaller parts, and delegate them to subthreads.
"""

import re
import json
import logging
import threading
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

from ..message import Message
from .base import ToolSpec
from .python import register_function

if TYPE_CHECKING:
    # noreorder
    from ..logmanager import LogManager  # fmt: skip

logger = logging.getLogger(__name__)

Status = Literal["running", "success", "failure"]

_subthreads = []


@dataclass
class ReturnType:
    status: Status
    result: str | None = None


@dataclass
class Subthread:
    prompt: str
    thread_id: str
    thread: threading.Thread

    def get_log(self) -> "LogManager":
        # noreorder
        from devopsx.cli import get_logfile  # fmt: skip

        from ..logmanager import LogManager  # fmt: skip

        name = f"subthread-{self.thread_id}"
        logfile = get_logfile(name, interactive=False)
        return LogManager.load(logfile)

    def status(self) -> ReturnType:
        if self.thread.is_alive():
            return ReturnType("running")
        # check if the last message contains the return JSON
        msg = self.get_log().log[-1].content.strip()
        json_response = _extract_json(msg)
        if not json_response:
            print(f"FAILED to find JSON in message: {msg}")
            return ReturnType("failure")
        elif not json_response.strip().startswith("{"):
            print(f"FAILED to parse JSON: {json_response}")
            return ReturnType("failure")
        else:
            return ReturnType(**json.loads(json_response))  # type: ignore


def _extract_json_re(s: str) -> str:
    return re.sub(
        r"(?s).+?(```json)?\n([{](.+?)+?[}])\n(```)?",
        r"\2",
        s,
    ).strip()


def _extract_json(s: str) -> str:
    first_brace = s.find("{")
    last_brace = s.rfind("}")
    return s[first_brace : last_brace + 1]


@register_function
def subthread(prompt: str, thread_id: str):
    """Runs a subthread and returns the resulting JSON output."""
    # noreorder
    from devopsx import chat  # fmt: skip

    from ..prompts import get_prompt  # fmt: skip

    name = f"subthread-{thread_id}"

    def run_subthread():
        prompt_msgs = [Message("user", prompt)]
        initial_msgs = [get_prompt()]

        # add the return prompt
        return_prompt = """When done with the task, please end with a JSON response on the format:
```json
{
    result: 'A description of the task result/outcome',
    status: 'success' | 'failure',
}
```"""
        initial_msgs[0].content += "\n\n" + return_prompt

        chat(
            prompt_msgs,
            initial_msgs,
            name=name,
            model=None,
            stream=False,
            no_confirm=True,
            interactive=False,
            show_hidden=False,
        )

    # start a thread with a subthread
    t = threading.Thread(
        target=run_subthread,
        daemon=True,
    )
    t.start()
    _subthreads.append(Subthread(prompt, thread_id, t))


@register_function
def subthread_status(thread_id: str) -> dict:
    """Returns the status of a subthread."""
    for subthread in _subthreads:
        if subthread.thread_id == thread_id:
            return asdict(subthread.status())
    raise ValueError(f"Subthread with ID {thread_id} not found.")


@register_function
def subthread_wait(thread_id: str) -> dict:
    """Waits for a subthread to finish. Timeout is 1 minute."""
    subthread = None
    for subthread in _subthreads:
        if subthread.thread_id == thread_id:
            break

    if subthread is None:
        raise ValueError(f"Subthread with ID {thread_id} not found.")

    print("Waiting for the subthread to finish...")
    subthread.thread.join(timeout=60)
    status = subthread.status()
    return asdict(status)


examples = """
User: compute fib 69 using a subthread
Assistant: Starting a subthread to compute the 69th Fibonacci number.
```python
subthread("compute the 69th Fibonacci number", "fib-69")
```
System: Subthread started successfully.
Assistant: Now we need to wait for the subthread to finish the task.
```python
subthread_wait("fib-69")
```
"""

tool = ToolSpec(
    name="subthread",
    desc="A tool to create subthreads",
    examples=examples,
    functions=[subthread, subthread_status, subthread_wait],
)

__doc__ = tool.get_doc(__doc__)