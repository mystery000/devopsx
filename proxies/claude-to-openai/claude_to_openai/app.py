import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from adapter import ClaudeAdapter
from logger import logger
from models import models_list

CLAUDE_BASE_URL = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
PORT = os.getenv("PORT", 8000)

logger.debug(f"claude_base_url: {CLAUDE_BASE_URL}")

adapter = ClaudeAdapter(CLAUDE_BASE_URL)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods, including OPTIONS
    allow_headers=["*"],
)

@app.api_route(
    "/v1/chat/completions",
    methods=["POST", "OPTIONS"],
)
async def chat(request: Request):
    openai_params = await request.json()
    if openai_params.get("stream", False):

        async def generate():
            async for response in adapter.chat(request):
                if response == "[DONE]":
                    yield "data: [DONE]"
                    break
                yield f"data: {json.dumps(response)}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        openai_response = None
        response = adapter.chat(request)
        openai_response = await response.__anext__()
        return JSONResponse(content=openai_response)


@app.route("/v1/models", methods=["GET"])
async def models(request: Request):
    return JSONResponse(content={"object": "list", "data": models_list})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, log_level=LOG_LEVEL)  # type: ignore
