import pytest
from devopsx.message import len_tokens
from devopsx.prompts import get_prompt
from devopsx.tools import init_tools


@pytest.fixture(scope="module", autouse=True)
def init():
    init_tools()


def test_get_prompt_full():
    prompt = get_prompt("full")
    # TODO: lower this significantly by selectively removing examples from the full prompt
    assert 500 < len_tokens(prompt.content) < 5000


def test_get_prompt_short():
    prompt = get_prompt("short")
    assert 500 < len_tokens(prompt.content) < 2000


def test_get_prompt_custom():
    prompt = get_prompt("Hello world!")
    assert prompt.content == "Hello world!"