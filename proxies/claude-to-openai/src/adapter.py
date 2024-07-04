import os
import time
from typing import Dict
from fastapi import Request
from util import num_tokens_from_string
from anthropic import AsyncAnthropic
from anthropic.types import Message, RawContentBlockDeltaEvent

class ClaudeAdapter:
    def __init__(self, claude_base_url="https://api.anthropic.com"):
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", None)
        self.claude_base_url = claude_base_url

    def get_api_key(self, headers):
        auth_header = headers.get("authorization", None)
        if auth_header:
            return auth_header.split(" ")[1]
        else:
            return self.claude_api_key

    def claude_to_chatgpt_response_stream(self, claude_response: RawContentBlockDeltaEvent, metadata: Dict[str, str]):
        content = claude_response.delta.text  # type: ignore
        completion_tokens = num_tokens_from_string(content)
        openai_response = {
            "id": f"chatcmpl-{str(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": metadata["model"],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": completion_tokens,
                "total_tokens": completion_tokens,
            },
            "choices": [
                {
                    "delta": {
                        "role": metadata["role"],
                        "content": content,
                    },
                    "index": claude_response.index,
                }
            ],
        }

        return openai_response

    def claude_to_chatgpt_response(self, claude_response: Message):
        prompt_tokens = claude_response.usage.input_tokens
        completion_tokens = claude_response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens

        openai_response = {
            "id": f"chatcmpl-{str(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": claude_response.model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "choices": [
                {
                    "message": {
                        "role": claude_response.role,
                        "content": claude_response.content[0].text,  # type: ignore
                    },
                    "index": 0,
                }
            ],
        }

        return openai_response

    def openai_to_claude_params(self, openai_params):
        claude_params = {
            "max_tokens": openai_params.get("max_tokens", 1024),
            "model": openai_params.get("model", "claude-3-5-sonnet-20240620")
        }

        claude_messages = [] 
        for message in openai_params.get("messages", []):
            if message["role"] == "system":
                claude_messages.append({
                    "role": "user",
                    "content": message["content"],
                })
                claude_messages.append({
                    "role": "assistant",
                    "content": ".",
                })
            else:
                claude_messages.append(message)

        claude_params["messages"] = claude_messages

        if openai_params.get("temperature"):
            claude_params["temperature"] = openai_params.get("temperature")

        if openai_params.get("stream"):
            claude_params["stream"] = True

        return claude_params

    async def chat(self, request: Request):
        openai_params = await request.json()
        headers = request.headers
        
        claude_params = self.openai_to_claude_params(openai_params)

        api_key = self.get_api_key(headers)

        client = AsyncAnthropic(api_key=api_key, timeout=120)

        if not claude_params.get("stream", False):
            claude_response = await client.messages.create(
                max_tokens=claude_params.get("max_tokens", 1024),
                messages=claude_params.get("messages", []),
                model=claude_params.get("model", "claude-3-5-sonnet-20240620")
            )
            openai_response = self.claude_to_chatgpt_response(claude_response)
            yield openai_response
        else:
            async with client.messages.stream(
                max_tokens=claude_params.get("max_tokens", 1024),
                messages=claude_params.get("messages", []),
                model=claude_params.get("model", "claude-3-5-sonnet-20240620")
            ) as stream:
                async for event in stream:
                    if event.type == "message_start":
                        model = event.message.model
                        role = event.message.role
                    if event.type == "message_stop":
                        yield "[DONE]"
                    if event.type == "content_block_delta":
                        yield self.claude_to_chatgpt_response_stream(event, metadata={"model": model, "role": role })