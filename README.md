[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/anansitrading-poe-proxy-mcp-badge.png)](https://mseep.ai/app/anansitrading-poe-proxy-mcp)

# Poe Proxy MCP Server

A FastMCP server that proxies the Poe.com API, exposing tools for querying Poe models and sharing files. This server is specifically designed to ensure compatibility with Claude 3.7 Sonnet and other models available through Poe.

## Features

- **Multiple Model Support**: Query various models available on Poe including GPT-4o, Claude 3 Opus, Claude 3 Sonnet, Gemini Pro, and more
- **Claude 3.7 Sonnet Compatibility**: Special handling for Claude's thinking protocol
- **File Sharing**: Share files with models that support it
- **Session Management**: Maintain conversation context across multiple queries
- **Streaming Responses**: Get real-time streaming responses from models
- **Web Client Support**: Use the server with web clients via SSE transport

## Installation

### Prerequisites

- Python 3.8 or higher
- A Poe API key (get one from [Poe.com](https://poe.com/api_key))

### Quick Installation

Use the provided installation script:

```bash
git clone https://github.com/Anansitrading/poe-proxy-mcp.git
cd poe-proxy-mcp
chmod +x install.sh
./install.sh
```

The script will:
1. Create a virtual environment
2. Install all dependencies
3. Create a `.env` file if it doesn't exist
4. Set up the server for both STDIO and SSE transports

### Manual Setup

If you prefer to set up manually:

1. Clone this repository:
   ```bash
   git clone https://github.com/Anansitrading/poe-proxy-mcp.git
   cd poe-proxy-mcp
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Poe API key:
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

### Installation as a Package

You can also install the server as a Python package:

```bash
pip install -e .
```

This will make the `poe-mcp` and `poe-mcp-sse` commands available in your environment.

## Configuration

The server can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `POE_API_KEY` | Your Poe API key (required) | None |
| `DEBUG_MODE` | Enable verbose logging | `false` |
| `CLAUDE_COMPATIBLE` | Enable Claude compatibility mode | `true` |
| `MAX_FILE_SIZE_MB` | Maximum file size for uploads | `10` |
| `SESSION_EXPIRY_MINUTES` | Session expiry duration in minutes | `60` |

## Usage

### Running the Server

#### Standard Mode (STDIO)

This is the default mode and is suitable for command-line usage:

```bash
# If installed as a package:
poe-mcp

# Or directly:
python poe_server.py
```

#### Web Mode (SSE)

This mode enables the server to be used with web clients:

```bash
# If installed as a package:
poe-mcp-sse [port]

# Or directly:
python run_sse_server.py [port]
```

The server will start on port 8000 by default, or you can specify a different port.

### Available Tools

The server exposes the following tools:

#### `ask_poe`

Ask a question to a Poe bot.

```python
response = await mcp.call("ask_poe", {
    "bot": "claude",  # or "o3", "gemini", "perplexity", "gpt"
    "prompt": "What is the capital of France?",
    "session_id": "optional-session-id",  # Optional
    "thinking": {  # Optional, for Claude models
        "thinking_enabled": True,
        "thinking_depth": 2
    }
})
```

#### `ask_with_attachment`

Ask a question to a Poe bot with a file attachment.

```python
response = await mcp.call("ask_with_attachment", {
    "bot": "claude",
    "prompt": "Analyze this code",
    "attachment_path": "/path/to/file.py",
    "session_id": "optional-session-id",  # Optional
    "thinking": {  # Optional, for Claude models
        "thinking_enabled": True
    }
})
```

#### `clear_session`

Clear a session's conversation history.

```python
response = await mcp.call("clear_session", {
    "session_id": "your-session-id"
})
```

#### `list_available_models`

List available Poe models and their capabilities.

```python
response = await mcp.call("list_available_models", {})
```

#### `get_server_info`

Get information about the server configuration.

```python
response = await mcp.call("get_server_info", {})
```

## Web Client

A simple web client is included in the `examples` directory. To use it:

1. Start the server in SSE mode:
   ```bash
   python run_sse_server.py
   ```

2. Open `examples/web_client.html` in your browser.

3. Enter the server URL (default: `http://localhost:8000`) and click "Get Available Models".

4. Select a model, enter your prompt, and click "Submit".

## Examples

### Simple Query

```python
# examples/simple_query.py
import asyncio
from fastmcp import MCPClient

async def main():
    client = MCPClient("http://localhost:8000")
    
    response = await client.call("ask_poe", {
        "bot": "claude",
        "prompt": "Explain quantum computing in simple terms"
    })
    
    print(f"Session ID: {response['session_id']}")
    print(f"Response: {response['text']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### File Attachment

```python
# examples/file_attachment.py
import asyncio
from fastmcp import MCPClient

async def main():
    client = MCPClient("http://localhost:8000")
    
    response = await client.call("ask_with_attachment", {
        "bot": "claude",
        "prompt": "Analyze this code and suggest improvements",
        "attachment_path": "examples/simple_query.py"
    })
    
    print(f"Session ID: {response['session_id']}")
    print(f"Response: {response['text']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Claude Compatibility

This server includes special handling for Claude models, particularly Claude 3.7 Sonnet, which requires specific formatting for the thinking protocol. When using Claude models:

1. The server automatically detects Claude models and applies the appropriate formatting.
2. You can enable the thinking protocol by providing a `thinking` parameter:
   ```python
   "thinking": {
       "thinking_enabled": True,
       "thinking_depth": 2,  # Optional, default is 1
       "thinking_style": "detailed"  # Optional
   }
   ```
3. If the thinking protocol fails, the server will automatically retry without it.

## Testing

To run the test suite:

```bash
python run_tests.py
```

For verbose output:

```bash
python run_tests.py --verbose
```

## Troubleshooting

### Common Issues

1. **Authentication Error**: Make sure your Poe API key is correct in the `.env` file.
2. **Connection Error**: Check that you can access Poe.com from your network.
3. **File Upload Error**: Ensure the file exists and is within the size limit.
4. **Claude Thinking Protocol Issues**: If you encounter errors with Claude's thinking protocol, try disabling it by setting `CLAUDE_COMPATIBLE=false` in your `.env` file.

### Debugging

Enable debug mode by setting `DEBUG_MODE=true` in your `.env` file for more detailed logs.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.