#!/usr/bin/env python3
"""
Example of using the Poe Proxy MCP server with file attachments.
"""
import os
import sys
import asyncio
import tempfile
from fastmcp.client import Client

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


async def main():
    """Run the example."""
    # Connect to the server using STDIO transport
    # Replace with the path to your poe_server.py
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'poe_server.py'))
    
    # Create a temporary text file for the example
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("This is a sample text file.\n")
        temp_file.write("It contains information about Paris, France.\n")
        temp_file.write("Paris is known as the City of Light.\n")
        temp_file.write("It is famous for the Eiffel Tower and the Louvre Museum.\n")
        temp_file_path = temp_file.name
    
    try:
        print(f"Connecting to server at: {server_path}")
        async with Client(f"stdio://{server_path}") as client:
            # Ask a question with a file attachment
            print(f"Asking question with file attachment: {temp_file_path}")
            response = await client.call(
                "ask_with_attachment",
                bot="GPT-3.5-Turbo",
                prompt="Summarize the key points from this file about Paris:",
                attachment_path=temp_file_path
            )
            
            print(f"\nResponse: {response['text']}")
            print(f"Session ID: {response['session_id']}")
            
            # Continue the conversation using the session ID
            print("\nAsking follow-up question...")
            follow_up = await client.call(
                "ask_poe",
                bot="GPT-3.5-Turbo",
                prompt="What other famous landmarks are in Paris?",
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
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"Deleted temporary file: {temp_file_path}")


if __name__ == "__main__":
    asyncio.run(main())