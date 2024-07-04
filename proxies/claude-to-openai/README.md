This project converts the API of Anthropic's Claude model to the OpenAI Chat API format.

- ✨ Call Claude API like OpenAI ChatGPT API
- 💦 Support streaming response
- 🐻 Support `claude-instant-1.2`, `claude-2.1`, `claude-3-5-sonnet-20240620`, `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307` models
- 🌩️ Deploy by Cloudflare Workers or Docker

## Getting Started

You can run this project using Cloudflare Workers or Docker:

### Deployment

#### Using Docker

```bash
docker build --pull --no-cache -t claude-to-openai
docker run -p 8000:8000 claude-to-openai
```

The API will then be available at http://localhost:8000. API endpoint: `/v1/chat/completions`

### Usage

#### CLI

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CLAUDE_API_KEY" \
  -d '{
    "model": "claude-3-5-sonnet-20240620",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Conversion Details

The Claude Completion API has an endpoint `/v1/complete` which takes the following JSON request:

```json
{
  "prompt": "\n\nHuman: Hello, AI.\n\nAssistant: ",
  "model": "claude-3-sonnet-20240229",
  "max_tokens_to_sample": 100,
  "temperature": 1,
  "stream": true
}
```

And returns JSON with choices and completions.

The OpenAI Chat API has a similar `/v1/chat/completions` endpoint which takes:

```json
{
  "model": "claude-3-5-sonnet-20240620",
  "messages": [
    {
      "role": "user",
      "content": "Hello, AI."
    }
  ],
  "max_tokens": 100,
  "temperature": 1,
  "stream": true
}
```

And returns JSON with a response string.

This project converts between these two APIs, get completions from the Claude model and formatting them as OpenAI Chat responses.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
