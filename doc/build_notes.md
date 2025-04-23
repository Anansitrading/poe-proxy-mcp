# Build Notes

This document tracks research findings and implementation decisions for the Poe API Proxy MCP server.

## Research Findings

### Poe API

- **Source**: [snowby666/poe-api-wrapper](https://github.com/snowby666/poe-api-wrapper)
- **Summary**: A Python wrapper for Poe.com's API that provides access to various AI models including GPT-4, Claude, and others. Requires p-b and p-lat cookies for authentication.
- **Key Features**: 
  - Supports streaming responses
  - Handles file attachments
  - Maintains conversation context
  - Provides access to multiple AI models

### FastMCP

- **Source**: [jlowin/fastmcp](https://github.com/jlowin/fastmcp)
- **Summary**: A Python framework for building Model Context Protocol (MCP) servers. Provides a simple, Pythonic interface for creating tools, resources, and prompts.
- **Key Features**:
  - Supports multiple transport protocols (STDIO, SSE)
  - Error handling and logging
  - Context management
  - Tool and resource definitions

## Implementation Considerations

Based on previous work with Claude 3.7 Sonnet compatibility (as noted in project memories), we need to ensure:

1. Proper thinking protocol support
2. Session management to maintain conversation context
3. Error handling with automatic fallback for protocol issues
4. Support for both STDIO and SSE transports
5. Clean separation of concerns between the Poe API client and MCP server