from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devopsx.eval.main import EvalSpec


def check_output_mohamed(ctx):
    return "Mohamed" in ctx.stdout


tests: list["EvalSpec"] = [
    {
        "name": "whois-superuserlabs-ceo",
        "files": {},
        "run": "cat answer.txt",
        "prompt": "who is the manager of infractura team? write the answer to answer.txt",
        "expect": {
            "correct output": check_output_mohamed,
        },
    },
]