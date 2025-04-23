#!/usr/bin/env python3
"""
Run the Poe Proxy MCP server with SSE transport.

This script runs the Poe Proxy MCP server with Server-Sent Events (SSE) transport,
which allows it to be used with web clients.
"""
import os
import sys
import importlib.util
import argparse
from fastmcp.transports.sse import run_sse

# Get the path to the poe_server.py file
server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'poe_server.py'))

# Import the poe_server module
spec = importlib.util.spec_from_file_location("poe_server", server_path)
poe_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poe_server)


def main():
    """Entry point for the console script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Poe Proxy MCP server with SSE transport")
    parser.add_argument("port", nargs="?", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()
    
    print(f"Starting Poe Proxy MCP server with SSE transport on {args.host}:{args.port}")
    print(f"Access the server at http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print("Press Ctrl+C to stop the server")
    
    # Run the server with SSE transport
    run_sse(poe_server.mcp, host=args.host, port=args.port)


if __name__ == "__main__":
    main()