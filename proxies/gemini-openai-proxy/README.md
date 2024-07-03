# Gemini-OpenAI-Proxy

Gemini-OpenAI-Proxy is a proxy designed to convert the OpenAI API protocol to the Google Gemini Pro protocol. This enables seamless integration of OpenAI-powered functionalities into applications using the Gemini Pro protocol.

---

## Table of Contents

- [Gemini-OpenAI-Proxy](#gemini-openai-proxy)
  - [Table of Contents](#table-of-contents)
  - [Build](#build)
  - [Deploy](#deploy)
  - [Usage](#usage)
  - [Compatibility](#compatibility)
  - [License](#license)

---

## Build

To build the Gemini-OpenAI-Proxy, follow these steps:

```bash
docker build --pull --no-cache -t gemini-openai-proxy .
```

---

## Deploy

We recommend deploying Gemini-OpenAI-Proxy using Docker for a straightforward setup. Follow these steps to deploy with Docker:

```bash
docker run --restart=always -it -d -p 8080:8080 --name gemini gemini-openai-proxy
```

Adjust the port mapping (e.g., `-p 8080:8080`) as needed, and ensure that the Docker image version aligns with your requirements.

---

## Usage

Gemini-OpenAI-Proxy offers a straightforward way to integrate OpenAI functionalities into any application that supports custom OpenAI API endpoints. Follow these steps to leverage the capabilities of this proxy:

1. **Set Up OpenAI Endpoint:**
   Ensure your application is configured to use a custom OpenAI API endpoint. Gemini-OpenAI-Proxy seamlessly works with any OpenAI-compatible endpoint.

2. **Get Google AI Studio API Key:**
   Before using the proxy, you'll need to obtain an API key from [ai.google.dev](https://ai.google.dev). Treat this API key as your OpenAI API key when interacting with Gemini-OpenAI-Proxy.

3. **Integrate the Proxy into Your Application:**
   Modify your application's API requests to target the Gemini-OpenAI-Proxy, providing the acquired Google AI Studio API key as if it were your OpenAI API key.

   Example API Request (Assuming the proxy is hosted at `http://localhost:8080`):

   ```bash
   curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $YOUR_GOOGLE_AI_STUDIO_API_KEY" \
    -d '{
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Say this is a test!"}],
        "temperature": 0.7
    }'
   ```

   Alternatively, use Gemini Pro Vision:

   ```bash
   curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $YOUR_GOOGLE_AI_STUDIO_API_KEY" \
    -d '{
        "model": "gpt-4-vision-preview",
        "messages": [{"role": "user", "content": [
           {"type": "text", "text": "What’s in this image?"},
           {
             "type": "image_url",
             "image_url": {
               "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
             }
           }
        ]}],
        "temperature": 0.7
    }'
   ```

   If you already have access to the Gemini 1.5 Pro api, you can use:

   ```bash
   curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $YOUR_GOOGLE_AI_STUDIO_API_KEY" \
    -d '{
        "model": "gpt-4-turbo-preview",
        "messages": [{"role": "user", "content": "Say this is a test!"}],
        "temperature": 0.7
    }'
   ```

   Model Mapping:

   | GPT Model            | Gemini Model                 |
   | -------------------- | ---------------------------- |
   | gpt-3.5-turbo        | gemini-1.0-pro-latest        |
   | gpt-4                | gemini-1.5-flash-latest      |
   | gpt-4-turbo-preview  | gemini-1.5-pro-latest        |
   | gpt-4-vision-preview | gemini-1.0-pro-vision-latest |

   If you wish to map `gpt-4-vision-preview` to `gemini-1.5-pro-latest`, you can configure the environment variable `GPT_4_VISION_PREVIEW = gemini-1.5-pro-latest`. This is because `gemini-1.5-pro-latest` now also supports multi-modal data.

4. **Handle Responses:**
   Process the responses from the Gemini-OpenAI-Proxy in the same way you would handle responses from OpenAI.

Now, your application is equipped to leverage OpenAI functionality through the Gemini-OpenAI-Proxy, bridging the gap between OpenAI and applications using the Google Gemini Pro protocol.

## License

Gemini-OpenAI-Proxy is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
