#!/usr/bin/env python3
"""
Test script for the Poe API client wrapper.
"""
import os
import sys
import asyncio
import tempfile
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from poe_client import PoeClient, SessionManager
from utils import setup_logging

# Load environment variables from .env file
load_dotenv()

# Initialize logging
logger = setup_logging(debug_mode=True)


async def test_poe_client():
    """Test the Poe API client wrapper."""
    # Get API key from environment variable
    api_key = os.getenv("POE_API_KEY")
    if not api_key:
        logger.error("POE_API_KEY environment variable not set")
        return
    
    logger.info("Initializing Poe API client")
    client = PoeClient(api_key=api_key, debug_mode=True)
    
    # Test querying a model
    logger.info("Testing query_model")
    response = await client.query_model(
        bot_name="GPT-3.5-Turbo",
        prompt="What is the capital of France?",
    )
    
    logger.info(f"Response: {response['text']}")
    
    # Test querying with a file
    logger.info("Testing query_model_with_file")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("This is a sample text file.\n")
        temp_file.write("It contains information about Paris, France.\n")
        temp_file.write("Paris is known as the City of Light.\n")
        temp_file.write("It is famous for the Eiffel Tower and the Louvre Museum.\n")
        temp_file_path = temp_file.name
    
    try:
        response = await client.query_model_with_file(
            bot_name="GPT-3.5-Turbo",
            prompt="Summarize the key points from this file about Paris:",
            file_path=temp_file_path,
        )
        
        logger.info(f"Response with file: {response['text']}")
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            logger.debug(f"Deleted temporary file: {temp_file_path}")
    
    # Test getting available models
    logger.info("Testing get_available_models")
    models = client.get_available_models()
    logger.info(f"Available models: {models}")
    
    # Test getting model info
    logger.info("Testing get_model_info")
    model_info = client.get_model_info("GPT-3.5-Turbo")
    logger.info(f"Model info: {model_info}")


async def test_session_manager():
    """Test the session manager."""
    logger.info("Initializing session manager")
    session_manager = SessionManager(expiry_minutes=60)
    
    # Test creating a session
    logger.info("Testing create_session")
    session_id = session_manager.create_session()
    logger.info(f"Created session: {session_id}")
    
    # Test getting a session
    logger.info("Testing get_session")
    session = session_manager.get_session(session_id)
    logger.info(f"Got session: {session}")
    
    # Test updating a session
    logger.info("Testing update_session")
    success = session_manager.update_session(
        session_id=session_id,
        user_message="Hello",
        bot_message="Hi there!",
    )
    logger.info(f"Updated session: {success}")
    
    # Test getting messages
    logger.info("Testing get_messages")
    messages = session_manager.get_messages(session_id)
    logger.info(f"Got messages: {messages}")
    
    # Test deleting a session
    logger.info("Testing delete_session")
    success = session_manager.delete_session(session_id)
    logger.info(f"Deleted session: {success}")
    
    # Test get_or_create_session
    logger.info("Testing get_or_create_session")
    new_session_id = session_manager.get_or_create_session()
    logger.info(f"Got or created session: {new_session_id}")
    
    # Test cleanup_expired_sessions
    logger.info("Testing cleanup_expired_sessions")
    num_cleaned = session_manager.cleanup_expired_sessions()
    logger.info(f"Cleaned up {num_cleaned} expired sessions")


async def main():
    """Run the tests."""
    logger.info("Starting tests")
    
    # Test Poe API client
    await test_poe_client()
    
    # Test session manager
    await test_session_manager()
    
    logger.info("Tests completed")


if __name__ == "__main__":
    asyncio.run(main())