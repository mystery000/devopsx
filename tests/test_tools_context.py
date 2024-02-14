import shutil

import pytest
from devopsx.tools.context import ctags, gen_context_msg
from devopsx.tools.shell import ShellSession, set_shell


@pytest.fixture
def shell():
    shell = ShellSession()
    set_shell(shell)
    return shell


def test_gen_context_msg(shell):
    msg = gen_context_msg()
    assert "devopsx" in msg.content, f"Expected 'devopsx' in output: {msg.content}"
    assert "$ pwd" in msg.content, f"Expected 'pwd' in output: {msg.content}"


def test_ctags(shell):
    # if ctags not installed, skip
    if not shutil.which("ctags"):
        pytest.skip("ctags not installed")

    output = ctags()
    expected_strings = ["def", "class", "devopsx"]
    for s in expected_strings:
        assert s in output, f"Expected '{s}' in output: {output}"
