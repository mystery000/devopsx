import atexit
import logging
import readline
from dotenv import load_dotenv

from .config import load_config, config_path, set_config_value
from .dirs import get_readline_history_file
from .llm import init_llm
from .models import set_default_model, PROVIDERS, get_recommended_model
from .tabcomplete import register_tabcomplete
from .tools import init_tools
from .util import console

logger = logging.getLogger(__name__)

_init_done = False


def init(model: str | None, interactive: bool, tool_allowlist: list[str] | None, verbose: bool = True):
    global _init_done
    if _init_done:
        logger.warning("init() called twice, ignoring")
        return
    _init_done = True

    # init
    logger.debug("Started")
    load_dotenv()

    config = load_config()

    # get from config
    if not model:
        model = config.get_env("MODEL")

    if not model:  # pragma: no cover
        # auto-detect depending on if OPENAI_API_KEY or ANTHROPIC_API_KEY is set
        if config.get_env("OPENAI_API_KEY"):
            if verbose: print("Found OpenAI API key, using OpenAI provider")
            model = "openai"
        elif config.get_env("ANTHROPIC_API_KEY"):
            if verbose: print("Found Anthropic API key, using Anthropic provider")
            model = "anthropic"
        elif config.get_env("GROQ_API_KEY"):
            if verbose: print("Found Groq API key, using Groq provider")
            model = "groq"
        elif config.get_env("OLLAMA_HOST"):
            if verbose: print("Found local LLM provider, using local LLM provider")
            model = "local"
        elif config.get_env("OPENROUTER_API_KEY"):
            print("Found OpenRouter API key, using OpenRouter provider")
            model = "openrouter"
        # ask user for API key
        elif interactive:
            model, _ = ask_for_api_key()

    # fail
    if not model:
        raise ValueError("No API key found, couldn't auto-detect provider")

    if any(model.startswith(f"{provider}/") for provider in PROVIDERS):
        provider, model = model.split("/", 1)
    else:
        provider, model = model, None
        
    # set up API_KEY and API_BASE, needs to be done before loading history to avoid saving API_KEY
    init_llm(provider)

    if not model:
        model = get_recommended_model(provider)
        if verbose: 
            console.log(
                f"No model specified, using recommended model for provider: {model}"
            )
        
    set_default_model(model)

    if interactive:
        _load_readline_history()

        # for some reason it bugs out shell tests in CI
        register_tabcomplete()

    init_tools(tool_allowlist)


def init_logging(verbose):
    # log init
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    # set httpx logging to WARNING
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)


# default history if none found
# NOTE: there are also good examples in the integration tests
history_examples = [
    "What is love?",
    "Have you heard about an open-source app called ActivityWatch?",
    "Explain 'Attention is All You Need' in the style of Andrej Karpathy.",
    "Explain how public-key cryptography works as if I'm five.",
    "Write a Python script that prints the first 100 prime numbers.",
    "Find all TODOs in the current git project",
]

def _load_readline_history() -> None:  # pragma: no cover
    logger.debug("Loading history")
    # enabled by default in CPython, make it explicit
    readline.set_auto_history(True)
    # had some bugs where it grew to gigs, which should be fixed, but still good precaution
    readline.set_history_length(100)
    history_file = get_readline_history_file()
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        for line in history_examples:
            readline.add_history(line)

    atexit.register(readline.write_history_file, history_file)


def ask_for_api_key():  # pragma: no cover
    """Interactively ask user for API key"""
    print("No API key set for OpenAI, Anthropic, Groq or OpenRouter.")
    print(
        """You can get one at:
- OpenAI: https://platform.openai.com/account/api-keys
- Anthropic: https://console.anthropic.com/settings/keys
- Groq: https://console.groq.com/keys
- OpenRouter: https://openrouter.ai/settings/keys
        """
    )
    api_key = input("Your API key for OpenAI, Groq or Anthropic: ").strip()

    if api_key.startswith("sk-ant-"):
        provider = "anthropic"
        env_var = "ANTHROPIC_API_KEY"
    elif api_key.startswith("sk-or-"):
        provider = "openrouter"
        env_var = "OPENROUTER_API_KEY"
    elif api_key.startswith("gsk_"):
        provider = "groq"
        env_var = "GROQ_API_KEY"
    else:
        provider = "openai"
        env_var = "OPENAI_API_KEY"

    # TODO: test API key
    # Save to config
    set_config_value(f"env.{env_var}", api_key)
    print(f"API key saved to config at {config_path}")
    return provider, api_key