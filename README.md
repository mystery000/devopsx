devopsx
=====

Infractura.com brings you devopsx, which is an expansive multi-agent generative AI-based tool to manage system / network infrastructure, develop / deploy code, and manage local environments with natural language.

**Features:**

Code execution

-  Directly execute code (shell and Python) in your local environment.

-  Lets the assistant use commandline tools to work with files, access the web, etc.
  
-  Executed code maintains state in a REPL-like manner.

Read, write, and change files

-  Supports making incremental changes with a patch mechanism.
  
-  Pipe in context via stdin or as arguments.
  
-  Passing a filename as an argument will read the file and include it as context.

Self-correcting

-  Commands have their output fed back to the agent, allowing it to self-correct.

Support for many models

-  Including GPT-4 and any model that runs in llama.cpp

Misc

-  Tab completion

-  Automatic naming of conversations

**Installation instructions:**

pip install matplotlib pandas numpy pillow

git clone git@github.com:infractura/devopsx.git

cd devopsx

python3 -m venv .venv

source .venv/bin/activate

python -m pip install -e .

**System requirements:**

devopsx requires root access 

local user running devopsx requires sudo rights
  
  For example, append in sudoers file:
  
  [USER]  ALL=(ALL:ALL) NOPASSWD:ALL

**Known limitations:**

Force install via apt-get

Pseudo-shell issues

Insist that the tool write scripts to disk vs. execute in local environment

Insist to not truncate or scripts will be truncated.

**LLM ACCESS**

To use GPT4+ Requires an OpenAI API KEY

Example start command: devopsx --model gpt-4-1106-preview --prompt-system short

Warning, long std output will eat tokens.

