#!/usr/bin/env python3
"""
Simple example of using the Poe Proxy MCP server.
"""
import os
import sys
import asyncio
from fastmcp.client import Client

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def main():
    """Run the example."""
    # Connect to the server using STDIO transport
    # Replace with the path to your poe_server.py
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'poe_server.py'))
    
    print(f"Connecting to server at: {server_path}")
    async with Client(f"stdio://{server_path}") as client:
        # Ask a question
        print("Asking initial question...")
        response = await client.call(
            "ask_poe",
            bot="GPT-3.5-Turbo",
            prompt="What is the capital of France?"
        )
        
        print(f"\nResponse: {response['text']}")
        print(f"Session ID: {response['session_id']}")
        
        # Continue the conversation using the session ID
        print("\nAsking follow-up question...")
        follow_up = await client.call(
            "ask_poe",
            bot="GPT-3.5-Turbo",
            prompt="What is its population?",
            session_id=response["session_id"]
        )
        
        print(f"\nResponse: {follow_up['text']}")
        
        # Clear the session
        print("\nClearing session...")
        clear_result = await client.call(
            "clear_session",
            session_id=response["session_id"]
        )
        
        print(f"Clear result: {clear_result['status']} - {clear_result['message']}")


if __name__ == "__main__":
    asyncio.run(main())