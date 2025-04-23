#!/bin/bash
# Installation script for Poe Proxy MCP Server

set -e  # Exit on error

# Print colored messages
print_green() {
    echo -e "\033[0;32m$1\033[0m"
}

print_blue() {
    echo -e "\033[0;34m$1\033[0m"
}

print_red() {
    echo -e "\033[0;31m$1\033[0m"
}

print_yellow() {
    echo -e "\033[0;33m$1\033[0m"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_red "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$python_version < 3.8" | bc) -eq 1 ]]; then
    print_red "Python version $python_version is not supported. Please install Python 3.8 or higher."
    exit 1
fi

print_blue "Using Python $python_version"

# Create virtual environment
print_blue "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
print_blue "Installing dependencies..."
pip install --upgrade pip
pip install -e .

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_yellow "Creating .env file..."
    cp .env.example .env
    print_yellow "Please edit the .env file and add your Poe API key."
else
    print_green ".env file already exists."
fi

# Create logs directory
mkdir -p logs

print_green "Installation complete!"
print_green "To activate the virtual environment, run: source venv/bin/activate"
print_green "To run the server with STDIO transport, run: poe-mcp"
print_green "To run the server with SSE transport, run: poe-mcp-sse"
print_green "You can also run the server directly with: python poe_server.py"
print_green "Or with SSE transport: python run_sse_server.py [port]"

# Check if .env file contains POE_API_KEY
if ! grep -q "POE_API_KEY=" .env || grep -q "POE_API_KEY=$" .env || grep -q "POE_API_KEY=\"\"" .env; then
    print_yellow "WARNING: POE_API_KEY is not set in .env file."
    print_yellow "Please edit the .env file and add your Poe API key."
    print_yellow "You can get your API key from https://poe.com/api_key"
fi