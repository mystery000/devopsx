#!/bin/bash

current_python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_python_version="3.10"
echo "Current Python version: $current_python_version"

if [ "$(printf '%s\n' "$required_python_version" "$current_python_version" | sort -V | head -n1)" != "$required_python_version" ]; then
    echo "Installing Python $required_python_version..."
    sudo apt-get update
    sudo apt-get install -y python3.10 python3.10-venv
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
    echo "Python $required_python_version installed successfully."
fi

# Ensure the python3-venv package is installed
if ! dpkg -l | grep -q python3-venv; then
    echo "Installing python3-venv..."
    sudo apt-get install -y python3-venv
    echo "python3-venv installed successfully."
fi

# Activate virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
fi

pip install poetry
poetry install --extras "datascience"

# Deactivate virtual environment
deactivate

echo "Installation complete!"
