# Build Notes

This document tracks research findings and implementation decisions for the Poe API Proxy MCP server.

## Research Findings

### Official Poe API

- **Source**: [fastapi_poe](https://pypi.org/project/fastapi-poe/)
- **Documentation**: [External Application Guide](https://creator.poe.com/docs/external-application-guide)
- **Summary**: The official Python package for interacting with Poe's API, providing access to various AI models including GPT-4, Claude, and others. Requires a Poe API key for authentication.
- **Key Features**: 
  - Supports streaming responses through async generators
  - Rate limited to 500 requests per minute per user
  - Charges compute points directly from the account associated with the API key
  - Simple interface for querying Poe bots

#### Authentication

Authentication is handled via a Poe API key, which can be obtained from https://poe.com/api_key (only available for Poe subscribers).

#### Usage Examples

**Synchronous Example**:
```python
import fastapi_poe as fp
api_key = "<api_key>"   # ← replace with your API key
message = fp.ProtocolMessage(role="user", content="Hello world")
for partial in fp.get_bot_response_sync(
        messages=[message],
        bot_name="GPT-3.5-Turbo",
        api_key=api_key):
    print(partial)
```

**Asynchronous Example**:
```python
import asyncio
import fastapi_poe as fp
async def get_response():
    api_key = "<api_key>"  # ← replace with your API key
    message = fp.ProtocolMessage(role="user", content="Hello world")
    async for partial in fp.get_bot_response(
            messages=[message],
            bot_name="GPT-3.5-Turbo",
            api_key=api_key):
        print(partial)
def main():
    asyncio.run(get_response())
if __name__ == "__main__":
    main()
```

### FastMCP

- **Source**: [jlowin/fastmcp](https://github.com/jlowin/fastmcp)
- **Summary**: A Python framework for building Model Context Protocol (MCP) servers. Provides a simple, Pythonic interface for creating tools, resources, and prompts.
- **Key Features**:
  - Supports multiple transport protocols (STDIO, SSE)
  - Error handling and logging
  - Context management
  - Tool and resource definitions

#### Tool Definition Pattern

FastMCP uses a decorator pattern for defining tools:

```python
from fastmcp import FastMCP

# Create server
mcp = FastMCP("My MCP Server")

@mcp.tool()
def echo(text: str) -> str:
    """Echo the input text"""
    return text

# Run the server
if __name__ == "__main__":
    mcp.run()
```

#### Error Handling

FastMCP implements several error mitigation strategies:

| Feature               | Implementation Detail                     |
|-----------------------|-------------------------------------------|
| Input Validation      | Automatic type checking via Python annotations |
| Error Propagation     | Structured error messages per MCP spec |
| Connection Management | Async context managers for clean teardown |
| Fallback Mechanisms   | Automatic transport protocol fallback |

### Integration Approach

To integrate FastMCP with the Poe API, we'll create a proxy server that:

1. Defines MCP tools that map to Poe API operations
2. Handles authentication via environment variables
3. Supports file attachments using FastAPI's UploadFile
4. Implements streaming responses for real-time updates
5. Provides proper error handling and logging

#### File Handling

For file attachments, we'll use FastAPI's `UploadFile` class which provides:

- Streaming file handling with spooled temporary storage
- Metadata access (filename, content-type)
- File-like interface with `read()`, `seek()`, and `close()` methods

## Implementation Considerations

Based on previous work with Claude 3.7 Sonnet compatibility (as noted in project memories), we need to ensure:

1. Proper thinking protocol support
2. Session management to maintain conversation context
3. Error handling with automatic fallback for protocol issues
4. Support for both STDIO and SSE transports
5. Clean separation of concerns between the Poe API client and MCP server