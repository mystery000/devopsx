import logging
from dataclasses import dataclass
from typing import TypedDict

from typing_extensions import NotRequired

logger = logging.getLogger(__name__)


@dataclass
class ModelMeta:
    provider: str
    model: str
    context: int

    # price in USD per 1k tokens
    # if price is not set, it is assumed to be 0
    price_input: float = 0
    price_output: float = 0


class _ModelDictMeta(TypedDict):
    context: int

    # price in USD per 1k tokens
    price_input: NotRequired[float]
    price_output: NotRequired[float]


# default model
DEFAULT_MODEL: str | None = None

# known models metadata
# TODO: can we get this from the API?
MODELS: dict[str, dict[str, _ModelDictMeta]] = {
    # https://platform.openai.com/docs/models
    "openai": {
        # TRAINING DATA: Up to October 2023
        "gpt-4o": {
            "context": 128_000,
        },
        # TRAINING DATA: Up to Sep 2021
        "gpt-4": {
            "context": 8192,
            "price_input": 0.03,   # 0.03 USD per 1k input tokens
            "price_output": 0.06,  # 0.06 USD per 1k output tokens
        },
        # TRAINING DATA: Up to Dec 2023
        "gpt-4-turbo": {
            "context": 128_000,
        },
        # TRAINING DATA: Up to Apr 2023
        "gpt-4-1106-preview": {
            "context": 128_000,
        },
        # TRAINING DATA: Up to Apr 2023
        "gpt-4-vision-preview": {
            "context": 128_000,
        },
        # TRAINING DATA: Up to Dec 2023
        "gpt-4-turbo-preview": {
            "context": 128_000,
        },
        # TRAINING DATA: Up to Sep 2021
        "gpt-3.5-turbo": {
            "context": 16385,
            "price_input": 0.001,  # 0.001 USD per 1k input tokens
            "price_output": 0.002, # 0.002 USD per 1k output tokens
        },
        # TRAINING DATA: Up to Sep 2021
        "gpt-3.5-turbo-16k": {
            "context": 16385,
        },
        # TRAINING DATA: Up to Sep 2021
        "gpt-3.5-turbo-1106": {
            "context": 16385,
        },
      
    },
    # https://ai.google.dev/gemini-api/docs/models/gemini
    "google": {
        # TRAINING DATA: Up to April 2024
        "gemini-1.5-pro-latest": {
            "context": 1_048_576,
        },
        # TRAINING DATA: Up to February 2024
        "gemini-1.0-pro-latest": {
            "context": 30720,
        },
        "gemini-1.0-ultra-latest": {
            "context": 128_000,
        },
        # TRAINING DATA: December 2023
        "gemini-1.0-pro-vision-latest": {
            "context": 12288,
        },        
        "gemini-1.5-flash-latest": {
            "context": 1_048_576
        },
    },
    # https://console.groq.com/docs/models
    "groq": {
        "llama3-8b-8192": {
            "context": 8192
        },
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


def set_default_model(model: str) -> None:
    assert get_model(model)
    global DEFAULT_MODEL
    DEFAULT_MODEL = model


def get_model(model: str | None = None) -> ModelMeta:
    if model is None:
        assert DEFAULT_MODEL, "Default model not set, set it with set_default_model()"
        model = DEFAULT_MODEL

    if "/" in model:
        provider, model = model.split("/")
        if provider not in MODELS or model not in MODELS[provider]:
            logger.warning(
                f"Model {provider}/{model} not found, using fallback model metadata"
            )
            return ModelMeta(provider=provider, model=model, context=4000)
    else:
        # try to find model in all providers
        for provider in MODELS:
            if model in MODELS[provider]:
                break
        else:
            logger.warning(f"Model {model} not found, using fallback model metadata")
            return ModelMeta(provider="unknown", model=model, context=4000)

    return ModelMeta(
        provider=provider,
        model=model,
        **MODELS[provider][model],
    )
