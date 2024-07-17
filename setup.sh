#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

# Check Python version and install if needed
current_python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_python_version="3.10"
echo "Installed Python version: $current_python_version"

if [ "$(printf '%s\n' "$required_python_version" "$current_python_version" | sort -V | head -n1)" != "$required_python_version" ]; then
    echo "Installing Python $required_python_version..."
    sudo apt-get update
    sudo apt-get install -y python3.10
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
fi

# Ensure the python3-venv package is installed
if ! dpkg -l | grep -q python3.10-venv; then
    echo "Installing python3.10-venv..."
    sudo apt-get install -y python3.10-venv
    echo "python3.10-venv installed successfully."
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
