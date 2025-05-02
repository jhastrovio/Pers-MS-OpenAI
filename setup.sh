#!/bin/bash

# Exit on first error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
CYAN='\033[0;36m'

echo -e "${GREEN}Setting up development environment...${NC}"

# Detect OS and set Python command
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash/Cygwin)
    PYTHON_CMD="python"
else
    # Unix-like systems
    PYTHON_CMD="python3"
fi

# Check if Python is installed and get version
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}Python is not installed or not in PATH.${NC}"
    echo -e "${RED}Please install Python 3.8 or higher and ensure it's in your PATH.${NC}"
    echo -e "${YELLOW}On Windows, make sure to check 'Add Python to PATH' during installation.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${YELLOW}Found Python version: ${PYTHON_VERSION}${NC}"

# Check if virtualenv is installed
if ! $PYTHON_CMD -m pip list | grep -q virtualenv; then
    echo -e "${YELLOW}Installing virtualenv...${NC}"
    $PYTHON_CMD -m pip install --user virtualenv
fi

# Remove existing venv if it's broken
if [ -d ".venv" ] && { [ ! -f ".venv/bin/activate" ] && [ ! -f ".venv/Scripts/activate" ]; }; then
    echo -e "${YELLOW}Found broken virtual environment, removing...${NC}"
    rm -rf .venv
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv .venv
    
    # Verify venv creation
    if { [ ! -f ".venv/bin/activate" ] && [ ! -f ".venv/Scripts/activate" ]; }; then
        echo -e "${RED}Failed to create virtual environment. Please check your Python installation.${NC}"
        exit 1
    fi
fi

# Activate virtual environment (handle both Unix and Windows paths)
echo -e "${YELLOW}Activating virtual environment...${NC}"
if [ -f ".venv/Scripts/activate" ]; then
    # Windows
    source .venv/Scripts/activate
else
    # Unix
    source .venv/bin/activate
fi

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}Failed to activate virtual environment.${NC}"
    exit 1
fi

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}requirements.txt not found${NC}"
    exit 1
fi

if [ -f "requirements-test.txt" ]; then
    pip install -r requirements-test.txt
else
    echo -e "${RED}requirements-test.txt not found${NC}"
    exit 1
fi

# Create config directory if it doesn't exist
if [ ! -d "config" ]; then
    echo -e "${YELLOW}Creating config directory...${NC}"
    mkdir -p config
fi

# Create secrets.json from template if it doesn't exist
if [ ! -f "config/secrets.json" ] && [ -f "config/secrets.json.template" ]; then
    echo -e "${YELLOW}Creating secrets.json template...${NC}"
    cp config/secrets.json.template config/secrets.json
    echo -e "${RED}Please update config/secrets.json with your credentials${NC}"
elif [ ! -f "config/secrets.json.template" ]; then
    echo -e "${RED}secrets.json.template not found${NC}"
    exit 1
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "${CYAN}Virtual environment is now activated.${NC}"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    echo -e "${CYAN}To activate the virtual environment in the future, run: source .venv/Scripts/activate${NC}"
else
    echo -e "${CYAN}To activate the virtual environment in the future, run: source .venv/bin/activate${NC}"
fi
echo -e "${CYAN}To deactivate, run: deactivate${NC}" 