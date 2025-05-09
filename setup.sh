#!/bin/bash

# Exit on first error
set -e

echo "Setting up development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed or not in PATH. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-test.txt

echo -e "\nSetup complete!"
echo "To activate the virtual environment in the future, run: source .venv/bin/activate"
echo "To deactivate, run: deactivate"
echo "To run the local server, use: uvicorn app:app --reload" 