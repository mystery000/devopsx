## Infractura DevOpsX

#### Overview

Infractura.com presents DevOpsX, a comprehensive multi-agent generative AI-based tool designed to oversee system/network infrastructure, facilitate code development/deployment, and manage local environments using natural language.

#### Features

- **Code Execution**
  - Direct execution of code (shell and Python) in the local environment.
  - Use of command-line tools to interact with files, access the web, etc.
  - Executed code maintains state in a REPL-like manner.
- **File Operations**
  - Support for making incremental changes with a patch mechanism.
  - Ability to pipe in context via stdin or as arguments.
  - Reading files by passing filenames as arguments to include them as context.
- **Self-Correcting**
  - Commands have their output fed back to the agent, allowing it to self-correct.
- **Model Support**
  - Use OpenAI, Azure, Anthropic, Gemini, GROQ or serve locally with `llama.cpp`
- **Miscellaneous**
  - Tab completion.
  - Automatic naming of conversations.

#### Installation Instructions

To install DevOpsX, follow these steps:

1. Clone the repository:
   ```
   git clone git@github.com:infractura/devopsx.git
   ```
2. Navigate to the DevOpsX directory:
   ```
   cd devopsx
   ```
3. Set up a virtual environment:
   ```
   python3 -m venv .venv
   ```
4. Activate the virtual environment:
   ```
   source .venv/bin/activate
   ```
5. Install Poetry:
   ```
   pip install poetry
   ```
6. Install required dependencies:
   ```
   poetry install --extras "datascience"
   ```

#### Quick Installation

To install and run DevOpsX, follow these steps

1. Clone the repository:
   ```
   git clone git@github.com:infractura/devopsx.git
   ```
2. Navigate to the DevOpsX directory:
   ```
   cd devopsx
   ```
3. Install DevOpsX:
   ```
   ./setup.sh
   ```
4. Run DevOpsX:
   ```
   ./devopsx.sh
   ```

#### Update DevOpsX

To install and run DevOpsX, follow these steps

1. Navigate to the DevOpsX directory
2. Pull the changes from git repository:
   ```
   git pull
   ```
3. Update the dependencies:
   ```
   ./setup.sh
   ```
4. Run DevOpsX:
   ```
   ./devopsx.sh
   ```

#### System Requirements

- DevOpsX requires root access.
- The local user running DevOpsX requires sudo rights. For example, append the following entry in the sudoers file:
  ```
  [USER]  ALL=(ALL:ALL) NOPASSWD:ALL
  ```

#### Known Limitations:

- Insistence that the tool write scripts to disk versus executing in the local environment.
- A warning to avoid truncation, as scripts will be truncated.

#### LLM Access

To use GPT-4+, an OpenAI API KEY is required. Example start command:

```
devopsx --llm openai --model gpt-4-1106-preview
```

##### Available OpenAI models
- gpt-4o-mini
- gpt-4o
- gpt-4
- gpt-4-turbo
- gpt-4-1106-preview
- gpt-4-vision-preview
- gpt-4-turbo-preview
- gpt-3.5-turbo
- gpt-3.5-turbo-16k
- gpt-3.5-turbo-1106

To use Gemini models, an Gemini API KEY is required. Example start command:

```
devopsx --llm google --model gemini-1.5-pro-latest
```

##### Available Gemini models

- gemini-1.5-pro-latest
- gemini-1.0-pro-latest
- gemini-1.0-ultra-latest
- gemini-1.0-pro-vision-latest

To use GROQ models, an GROQ API KEY is required. Example start command:

```
devopsx --llm groq --model llama3-8b-8192
```

##### Available Gemini models

- llama3-8b-8192
- llama3-70b-8192
- mixtral-8x7b-32768
- gemma-7b-it

To use Claude family of models, an ANTHROPIC API KEY is required. Example start command:

```
devopsx --llm anthropic --model claude-3-5-sonnet-20240620
```

##### Available Gemini models

- claude-instant-1.2
- claude-2.1
- claude-3-5-sonnet-20240620
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307

**Caution:** Long stdout output will consume tokens.
