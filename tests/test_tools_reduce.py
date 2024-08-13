from pathlib import Path

import pytest
from devopsx.message import Message
from devopsx.tools.reduce import reduce_log, truncate_msg
from devopsx.util import len_tokens

# Project root
root = Path(__file__).parent.parent

# Some large files
readme = root / "README.md"
cli = root / "devopsx" / "cli.py"
htmlindex = root / "static" / "index.html"

long_msg = Message(
    "system",
    content="\n\n".join(
        f"```{fn.name}\n{open(fn).read()}\n```" for fn in [cli, htmlindex]
    ),
)


def test_truncate_msg():
    len_pre = len_tokens(long_msg)
    truncated = truncate_msg(long_msg)
    assert truncated is not None
    len_post = len_tokens(truncated)
    assert len_pre > len_post
    assert "[...]" in truncated.content
    assert "```cli.py" in truncated.content
    assert "```index.html" in truncated.content


@pytest.mark.slow
def test_reduce_log():
    msgs = [
        Message("system", content="system prompt"),
        Message("user", content=" ".join(fn.name for fn in [readme, cli, htmlindex])),
        long_msg,
    ]
    len_pre = len_tokens(msgs)
    print(f"{len_pre=}")

    limit = 1000
    reduced = list(reduce_log(msgs, limit=limit))
    len_post = len_tokens(reduced)
    print(f"{len_post=}")
    print(f"{reduced[-1].content=}")

    assert len_pre > len_post
    assert len_post < limit
