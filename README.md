# Poe Proxy MCP Server

A FastMCP v2 server that proxies the Poe.com API, supporting both STDIO and SSE transports.

## Overview

This project provides a Model Context Protocol (MCP) server that acts as a proxy for the Poe.com API, allowing you to query various AI models including GPT-4, Claude, and others through a standardized interface. The server supports both STDIO and SSE transports, making it compatible with a wide range of MCP clients.

## Features

- Query Poe models through MCP tools
- Maintain conversation context with session management
- Support for file attachments
- Streaming responses for real-time updates
- Proper error handling and logging
- Claude 3.7 Sonnet compatibility

## Prerequisites

- Python 3.9 or higher
- A Poe.com API key (available for Poe subscribers at https://poe.com/api_key)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Anansitrading/poe-proxy-mcp.git
   cd poe-proxy-mcp
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Poe API key:
   ```bash
   echo "POE_API_KEY=your_api_key_here" > .env
   ```

## Usage

### Running the Server

To run the server with STDIO transport (default):

```bash
python poe_server.py
```

To run the server with SSE transport:

```bash
python -m fastmcp.transports.sse poe_server.py
```

### Available Tools

The server exposes the following MCP tools:

#### 1. `ask_poe`

Query a Poe bot with a text prompt.

Parameters:
- `bot` (string): The bot to ask (e.g., "GPT-3.5-Turbo", "Claude-3-Opus")
- `prompt` (string): The text prompt to send to the bot
- `thinking` (object, optional): Parameters for Claude's thinking protocol
- `session_id` (string, optional): Session ID for maintaining conversation context

Returns:
- `text` (string): The response from the bot
- `session_id` (string): The session ID for future queries

#### 2. `ask_with_attachment`

Query a Poe bot with a text prompt and a file attachment.

Parameters:
- `bot` (string): The bot to ask (e.g., "GPT-3.5-Turbo", "Claude-3-Opus")
- `prompt` (string): The text prompt to send to the bot
- `attachment_path` (string): Path to the file to attach
- `thinking` (object, optional): Parameters for Claude's thinking protocol
- `session_id` (string, optional): Session ID for maintaining conversation context

Returns:
- `text` (string): The response from the bot
- `session_id` (string): The session ID for future queries

#### 3. `clear_session`

Clear a session's conversation history.

Parameters:
- `session_id` (string): The session ID to clear

Returns:
- `status` (string): Success or error status
- `message` (string): Status message

### Environment Variables

The server can be configured using the following environment variables:

- `POE_API_KEY` (required): Your Poe API key
- `DEBUG_MODE` (optional): Set to "true" for verbose logging (default: "false")
- `USE_CLAUDE_COMPATIBLE` (optional): Set to "true" to enable Claude compatibility mode (default: "false")
- `MAX_FILE_SIZE_MB` (optional): Maximum file size in MB for file uploads (default: 10)
- `SESSION_EXPIRY_MINUTES` (optional): Session expiry time in minutes (default: 60)

## Examples

### Python Example

```python
from fastmcp.client import Client

# Connect to the server
client = Client("stdio://path/to/poe_server.py")

# Ask a question
response = client.call(
    "ask_poe",
    bot="GPT-3.5-Turbo",
    prompt="What is the capital of France?"
)

print(response["text"])

# Continue the conversation using the session ID
follow_up = client.call(
    "ask_poe",
    bot="GPT-3.5-Turbo",
    prompt="What is its population?",
    session_id=response["session_id"]
)

print(follow_up["text"])
```

## Troubleshooting

If you encounter any issues, check the logs in the `logs` directory for detailed error information.

Common issues:
- Missing or invalid Poe API key
- Rate limiting (Poe limits to 500 requests per minute per user)
- Network connectivity problems

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP server framework
- [fastapi_poe](https://pypi.org/project/fastapi-poe/) for the Poe API client