#!/bin/bash

echo "Checking if make is installed..."
if ! command -v make &> /dev/null; then
    echo "make not found. Installing make..."
    sudo apt-get update
    sudo apt-get install -y make
else
    echo "make is already installed."
fi

make build