import sys
import logging
from dataclasses import dataclass
from typing import TypedDict, Optional
from typing_extensions import NotRequired

logger = logging.getLogger(__name__)

@dataclass
class ModelMeta:
    provider: str
    model: str
    context: int
    max_output: Optional[int] = None
    price_input: float = 0
    price_output: float = 0


class _ModelDictMeta(TypedDict):
    context: int
    max_output: NotRequired[int]
    price_input: NotRequired[float]
    price_output: NotRequired[float]


# default model
DEFAULT_MODEL: ModelMeta | None = None

# known models metadata
# TODO: can we get this from the API?
MODELS: dict[str, dict[str, _ModelDictMeta]] = {
    # https://platform.openai.com/docs/models
    "openai": {
        "gpt-4o-mini": {
            "context": 128_000,
        },
        # Training data cut-off: October 2023
        "gpt-4o": {
            "context": 128_000,
        },
        # Training data cut-off: Sep 2021
        "gpt-4": {
            "context": 8192,
            "price_input": 0.03,   # 0.03 USD per 1k input tokens
            "price_output": 0.06,  # 0.06 USD per 1k output tokens
        },
        # Training data cut-off: Dec 2023
        "gpt-4-turbo": {
            "context": 128_000,
        },
        # Training data cut-off: Apr 2023
        "gpt-4-1106-preview": {
            "context": 128_000,
        },
        # Training data cut-off: Apr 2023
        "gpt-4-vision-preview": {
            "context": 128_000,
        },
        # Training data cut-off: Dec 2023
        "gpt-4-turbo-preview": {
            "context": 128_000,
        },
        # Training data cut-off: Sep 2021
        "gpt-3.5-turbo": {
            "context": 16385,
            "price_input": 0.001,  # 0.001 USD per 1k input tokens
            "price_output": 0.002, # 0.002 USD per 1k output tokens
        },
        # Training data cut-off: Sep 2021
        "gpt-3.5-turbo-16k": {
            "context": 16385,
        },
        # Training data cut-off: Sep 2021
        "gpt-3.5-turbo-1106": {
            "context": 16385,
        },
      
    },
    # https://ai.google.dev/gemini-api/docs/models/gemini
    "google": {
        # Training data cut-off: April 2024
        "gemini-1.5-pro-latest": {
            "context": 1_048_576,
        },
        # Training data cut-off: February 2024
        "gemini-1.0-pro-latest": {
            "context": 30720,
        },
        "gemini-1.0-ultra-latest": {
            "context": 128_000,
        },
        # Training data cut-off: December 2023
        "gemini-1.0-pro-vision-latest": {
            "context": 12288,
        },        
        "gemini-1.5-flash-latest": {
            "context": 1_048_576
        },
    },
    # https://console.groq.com/docs/models
    "groq": {
        # Training data cut-off: March, 2023
        "llama3-8b-8192": {
            "context": 8192
        },
        # Training data cut-off: December, 2023
        "llama3-70b-8192": {
            "context": 8192
        },
        "mixtral-8x7b-32768": {
            "context": 32768
        },
        "gemma-7b-it": {
            "context": 8192
        }
    },
    # https://docs.anthropic.com/en/docs/about-claude/models
    "anthropic": {
        # Training data cut-off: Early 2023
        "claude-instant-1.2": {
            "context": 100_000,
            "price_input": 0.80,   # 0.80 USD per 1 MTok input tokens
            "price_output": 2.40,  # 2.40 USD per 1 MTok output tokens 	
        },
        # Training data cut-off: Early 2023
        "claude-2.1": {
            "context": 200_000,
            "price_input": 8.00,    # 8.00 USD per 1 MTok input tokens
            "price_output": 24.00,  # 24.00 USD per 1 MTok output tokens 	
        },
        # Training data cut-off: Apr 2024
        "claude-3-5-sonnet-20240620": {
            "context": 200_000,
            "max_output": 4096,
            "price_input": 3.00,    # 3.00 USD per 1 MTok input tokens
            "price_output": 15.00,  # 15.00 USD per 1 MTok output tokens 	
        },
        # Training data cut-off: Aug 2023
        "claude-3-opus-20240229": {
            "context": 200_000,
            "price_input": 15.00,   # 15.00 USD per 1 MTok input tokens
            "price_output": 75.00,  # 75.00 USD per 1 MTok output tokens 	
        },
        # Training data cut-off: Aug 2023
        "claude-3-sonnet-20240229": {
            "context": 200_000,
            "price_input": 3.00,    # 3.00 USD per 1 MTok input tokens
            "price_output": 15.00,  # 15.00 USD per 1 MTok output tokens 	
        },
        # Training data cut-off: Aug 2023
        "claude-3-haiku-20240307": {
            "context": 200_000,
            "price_input": 0.25,   # 0.25 USD per 1 MTok input tokens
            "price_output": 1.25,  # 1.25 USD per 1 MTok output tokens 	
        },
    }
}


def set_model(family: str, model: str) -> None:
    global DEFAULT_MODEL
    DEFAULT_MODEL = get_model(family, model)


def get_model(family: str | None = None, model: str | None = None) -> ModelMeta:
    if model is None and family is None:
        assert DEFAULT_MODEL, "Default model not set, set it with set_model()"
        return DEFAULT_MODEL

    if "/" in model:
        provider, model = model.split("/")
        if provider not in MODELS or model not in MODELS[provider]:
            print(f"Error: model {provider}/{model} cannot be found.")
            sys.exit(1)
        else:
            return ModelMeta(
                provider=provider,
                model=model,
                **MODELS[provider][model],
            )
    else:
        if model in MODELS[family]:
            return ModelMeta(
                provider=family,
                model=model,
                **MODELS[family][model],
            )
        else:    
            print(f"Error: model {model} cannot be found. Please select one of the following available models:\n" + "\n".join(MODELS[family]))
            sys.exit(1)

    