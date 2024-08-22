#!/bin/bash
set -euo pipefail

# Constants
MIN_DISK_SPACE_KB=819200  # Minimum required disk space in KB (e.g., 800MB)
REQUIRED_PYTHON_VERSION="3.11"

check_disk_space() {
  echo "🔍 Checking disk space..."
  local available_disk_space
  available_disk_space=$(df -k . | awk 'NR==2 {print $4}')
  if [ "$available_disk_space" -lt "$MIN_DISK_SPACE_KB" ]; then
    echo "❌ Not enough disk space. Required: $MIN_DISK_SPACE_KB KB, Available: $available_disk_space KB" >&2
    exit 1
  fi
  echo "✅ Enough disk space available."
}

install_make() {
  echo "Checking if make is installed..."
  if ! command -v make &> /dev/null; then
    echo "Installing make..."
    sudo apt-get update
    sudo apt-get install -y make
    echo "make installed successfully."
  else
    echo "make is already installed."
  fi
}

install_python() {
  local current_python_version
  current_python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
  echo "Current Python version: $current_python_version"

  if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$current_python_version" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]; then
    echo "Installing Python $REQUIRED_PYTHON_VERSION..."
    sudo apt-get update && sudo apt-get upgrade -y
    sudo apt-get install -y python3.11
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    echo "Python $REQUIRED_PYTHON_VERSION installed successfully."
  fi
}

install_python_venv() {
  if ! dpkg -l | grep -q python3.11-venv; then
    echo "Installing python3.11-venv..."
    sudo apt-get update
    sudo apt-get install -y python3.11-venv
    echo "python3.11-venv installed successfully."
  fi
}

setup_virtual_environment() {
  if [ -z "${VIRTUAL_ENV:-}" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install poetry
    poetry install --extras "datascience"
    deactivate
  fi
}

create_symlink() {
  local target="/usr/local/bin/devopsx"
  echo "Creating symbolic link to $target..."
  if [ -e "$target" ]; then
    echo "Symbolic link already exists. Skipping."
  else
    sudo ln -s "$(pwd)/.venv/bin/devopsx" "$target"
    echo "Symbolic link created."
  fi
}

main() {
  echo "🚀 Starting the setup process for devopsx... Please wait."
  echo
  check_disk_space
  echo
  install_make
  echo
  install_python
  echo
  install_python_venv
  echo
  setup_virtual_environment
  echo
  create_symlink
  echo "😊 Setup process for your tool completed successfully! You are ready to go."
}

main
