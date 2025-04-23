#!/usr/bin/env python3
"""
Run the Poe Proxy MCP server with SSE transport.

This script runs the Poe Proxy MCP server with Server-Sent Events (SSE) transport,
which allows it to be used with web clients.
"""
import os
import sys
import importlib.util
from fastmcp.transports.sse import run_sse

# Get the path to the poe_server.py file
server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'poe_server.py'))

# Import the poe_server module
spec = importlib.util.spec_from_file_location("poe_server", server_path)
poe_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poe_server)

# Run the server with SSE transport
if __name__ == "__main__":
    # Get the port from command line arguments or use default
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    print(f"Starting Poe Proxy MCP server with SSE transport on port {port}")
    print(f"Access the server at http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    # Run the server with SSE transport
    run_sse(poe_server.mcp, host="0.0.0.0", port=port)