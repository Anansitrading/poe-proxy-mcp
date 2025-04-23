#!/usr/bin/env python3
"""
Test script for Claude compatibility in the Poe Proxy MCP server.

This script tests the Claude thinking protocol compatibility by sending
requests with and without the thinking protocol enabled.
"""
import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastMCP client
try:
    from fastmcp import MCPClient
except ImportError:
    print("Error: fastmcp package not found. Please install it with:")
    print("pip install fastmcp")
    sys.exit(1)

# Load environment variables
load_dotenv()


async def test_claude_compatibility(server_url, verbose=False):
    """
    Test Claude compatibility with the Poe Proxy MCP server.
    
    Args:
        server_url: URL of the MCP server
        verbose: Whether to show verbose output
    """
    print(f"Testing Claude compatibility with server at {server_url}")
    
    # Create MCP client
    client = MCPClient(server_url)
    
    # Test 1: Basic query without thinking protocol
    print("\n=== Test 1: Basic query without thinking protocol ===")
    try:
        response = await client.call("ask_poe", {
            "bot": "claude",
            "prompt": "Explain quantum computing in one paragraph."
        })
        
        if "error" in response:
            print(f"Error: {response['error']}")
            print(f"Message: {response.get('message', 'No message')}")
        else:
            print("Success! Response received.")
            if verbose:
                print(f"Response text: {response['text']}")
            print(f"Session ID: {response['session_id']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test 2: Query with thinking protocol
    print("\n=== Test 2: Query with thinking protocol ===")
    try:
        response = await client.call("ask_poe", {
            "bot": "claude",
            "prompt": "Explain quantum computing in one paragraph.",
            "thinking": {
                "thinking_enabled": True,
                "thinking_depth": 2
            }
        })
        
        if "error" in response:
            print(f"Error: {response['error']}")
            print(f"Message: {response.get('message', 'No message')}")
        else:
            print("Success! Response with thinking protocol received.")
            if verbose:
                print(f"Response text: {response['text']}")
            print(f"Session ID: {response['session_id']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test 3: Get server info to check Claude compatibility
    print("\n=== Test 3: Check server Claude compatibility setting ===")
    try:
        response = await client.call("get_server_info", {})
        
        if "error" in response:
            print(f"Error: {response['error']}")
            print(f"Message: {response.get('message', 'No message')}")
        else:
            print("Server info:")
            print(f"  Name: {response['name']}")
            print(f"  Version: {response['version']}")
            print(f"  Claude compatible: {response['claude_compatible']}")
            print(f"  Debug mode: {response['debug_mode']}")
            print(f"  Active sessions: {response['active_sessions']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Test 4: List available models to check Claude models
    print("\n=== Test 4: Check available Claude models ===")
    try:
        response = await client.call("list_available_models", {})
        
        if "error" in response:
            print(f"Error: {response['error']}")
            print(f"Message: {response.get('message', 'No message')}")
        else:
            claude_models = [model for model in response["models"] if model.get("is_claude", False)]
            print(f"Found {len(claude_models)} Claude models:")
            for model in claude_models:
                print(f"  - {model['name']}")
                if verbose:
                    print(f"    Context length: {model['context_length']}")
                    print(f"    Supports images: {model['supports_images']}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print("\n=== Claude Compatibility Test Summary ===")
    print("If all tests passed, your server is properly configured for Claude compatibility.")
    print("If you encountered errors, check the following:")
    print("1. Ensure CLAUDE_COMPATIBLE=true is set in your environment")
    print("2. Verify your Poe API key has access to Claude models")
    print("3. Check that you're not using Docker or other containerization")
    print("4. Verify network connectivity to Poe's API servers")


async def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test Claude compatibility with the Poe Proxy MCP server")
    parser.add_argument("--url", type=str, default="http://localhost:8000", 
                        help="URL of the MCP server (default: http://localhost:8000)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Show verbose output including response text")
    
    args = parser.parse_args()
    
    await test_claude_compatibility(args.url, args.verbose)


if __name__ == "__main__":
    asyncio.run(main())