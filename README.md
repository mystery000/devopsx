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
  - Use OpenAI, Azure, Anthropic, Groq or serve locally with `llama.cpp`
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
devopsx --model openai/gpt-4-1106-preview
```

##### Available OpenAI models
- openai/gpt-4o-mini
- openai/gpt-4o
- openai/gpt-4
- openai/gpt-4-turbo
- openai/gpt-4-1106-preview
- openai/gpt-4-vision-preview
- openai/gpt-4-turbo-preview
- openai/gpt-3.5-turbo
- openai/gpt-3.5-turbo-16k
- openai/gpt-3.5-turbo-1106

To use GROQ models, an GROQ API KEY is required. Example start command:

```
devopsx --model groq/llama3-8b-8192
```

##### Available Gemini models

- groq/llama-3.1-70b-versatile
- groq/llama-3.1-8b-instant
- groq/llama3-8b-8192
- groq/llama3-70b-8192
- groq/mixtral-8x7b-32768
- groq/gemma-7b-it

To use Claude family of models, an ANTHROPIC API KEY is required. Example start command:

```
devopsx --model anthropic/claude-3-5-sonnet-20240620
```

##### Available Gemini models

- anthropic/claude-instant-1.2
- anthropic/claude-2.1
- anthropic/claude-3-5-sonnet-20240620
- anthropic/claude-3-opus-20240229
- anthropic/claude-3-sonnet-20240229
- anthropic/claude-3-haiku-20240307

**Caution:** Long stdout output will consume tokens.