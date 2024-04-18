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
  - Integration with various models, including GPT-4 and any model that runs in llama.cpp.
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
To install and run DevopsX, follow these steps
1. Clone the repository:
   ```
   git clone git@github.com:infractura/devopsx.git
   ```
2. Navigate to the DevOpsX directory:
   ```
   cd devopsx
   ```
3. Install DevopsX:
   ```
   ./setup.sh
   ```
4. Run Devopsx:
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
- An issue with force installation via apt-get.
- Pseudo-shell issues.
- Insistence that the tool write scripts to disk versus executing in the local environment.
- A warning to avoid truncation, as scripts will be truncated.

#### LLM Access
To use GPT-4+, an OpenAI API KEY is required. Example start command: 
```
devopsx --model gpt-4-1106-preview --prompt-system short
```
**Caution:** Long stdout output will consume tokens.

For further access to GPT4+, please ensure to obtain an OpenAI API KEY.  