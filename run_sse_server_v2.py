#!/usr/bin/env python3
"""
Poe Proxy MCP SSE Server (SDK-Compatible Version)

A FastMCP server that proxies the Poe.com API, exposing tools for querying Poe models
and sharing files. This implementation follows the structure of the official Python MCP SDK
and uses the SSE transport protocol.
"""
import os
import sys
import asyncio
from typing import Dict, List, Optional, AsyncGenerator, Any, Union

# Import from the official MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.shared.context import RequestContext
except ImportError:
    raise ImportError(
        "The mcp package is not installed. Please install it with: pip install mcp"
    )

# Import our core implementation
from poe_server_v2 import (
    ask_poe,
    ask_with_attachment,
    clear_session,
    list_available_models,
    get_server_info,
    startup,
    logger,
    config,
)

# Create FastMCP server
mcp = FastMCP("Poe Proxy MCP SSE Server")

# Register tools
mcp.register_tool(ask_poe)
mcp.register_tool(ask_with_attachment)
mcp.register_tool(clear_session)
mcp.register_tool(list_available_models)
mcp.register_tool(get_server_info)

# Register startup handler
mcp.on_startup(startup)


def main():
    """Entry point for the console script."""
    # Get port from command line arguments or use default
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port: {sys.argv[1]}, using default port: {port}")
    
    logger.info(f"Starting Poe Proxy MCP SSE Server on port {port}")
    logger.info(f"Claude compatibility mode: {config.claude_compatible}")
    
    # Run the MCP server with SSE transport
    mcp.run(transport="sse", port=port)


if __name__ == "__main__":
    # Run the MCP server
    main()