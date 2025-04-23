#!/usr/bin/env python3
"""
Test script for the Poe Proxy MCP server.

This script tests the functionality of the Poe Proxy MCP server, including:
1. Basic queries with different Poe models
2. Session management
3. File sharing
4. Error handling
5. Claude compatibility
"""
import os
import sys
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import server modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import server modules
from poe_client.poe_api import PoeClient
from poe_client.session import SessionManager
from poe_client.claude_compat import format_thinking_protocol, process_claude_response
from utils.config import get_config

# Import FastMCP for in-process testing
from fastmcp import FastMCP
from fastmcp.client import Client


class TestPoeProxyServer(unittest.TestCase):
    """Test cases for the Poe Proxy MCP server."""

    def setUp(self):
        """Set up test environment."""
        # Load configuration
        self.config = get_config()
        
        # Create a mock PoeClient
        self.mock_poe_client = MagicMock(spec=PoeClient)
        self.mock_poe_client.query_model.return_value = {
            "text": "This is a test response",
            "status": "success"
        }
        self.mock_poe_client.query_model_with_file.return_value = {
            "text": "This is a test response for a file",
            "status": "success"
        }
        self.mock_poe_client.get_available_models.return_value = [
            "GPT-3.5-Turbo", "Claude-3-Sonnet-7k", "GPT-4o"
        ]
        self.mock_poe_client.get_model_info.return_value = {
            "description": "Test model",
            "context_length": 4096,
            "supports_images": True
        }
        
        # Create a session manager
        self.session_manager = SessionManager(expiry_minutes=10)
        
        # Create a temporary file for testing file sharing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(b"This is a test file for testing file sharing.")
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary file
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_ask_poe(self, mock_session_manager, mock_poe_client):
        """Test the ask_poe tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test basic query
        response = client.call("ask_poe", {
            "bot": "GPT-3.5-Turbo",
            "prompt": "Hello, world!"
        })
        
        # Check response
        self.assertIn("text", response)
        self.assertIn("session_id", response)
        self.assertEqual(response["text"], "This is a test response")
        
        # Test query with session ID
        session_id = response["session_id"]
        response = client.call("ask_poe", {
            "bot": "GPT-3.5-Turbo",
            "prompt": "Follow-up question",
            "session_id": session_id
        })
        
        # Check response
        self.assertEqual(response["session_id"], session_id)
        
        # Test query with thinking protocol for Claude
        response = client.call("ask_poe", {
            "bot": "Claude-3-Sonnet-7k",
            "prompt": "Hello, Claude!",
            "thinking": {
                "thinking_enabled": True,
                "thinking_depth": 2
            }
        })
        
        # Check response
        self.assertIn("text", response)
        self.assertIn("session_id", response)
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_ask_with_attachment(self, mock_session_manager, mock_poe_client):
        """Test the ask_with_attachment tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test file sharing
        response = client.call("ask_with_attachment", {
            "bot": "GPT-4o",
            "prompt": "Analyze this file",
            "attachment_path": self.temp_file.name
        })
        
        # Check response
        self.assertIn("text", response)
        self.assertIn("session_id", response)
        self.assertEqual(response["text"], "This is a test response for a file")
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_clear_session(self, mock_session_manager, mock_poe_client):
        """Test the clear_session tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Create a session
        session_id = self.session_manager.get_or_create_session(None)
        
        # Test clear session
        response = client.call("clear_session", {
            "session_id": session_id
        })
        
        # Check response
        self.assertEqual(response["status"], "success")
        
        # Test clear non-existent session
        response = client.call("clear_session", {
            "session_id": "non-existent-session"
        })
        
        # Check response
        self.assertEqual(response["status"], "error")
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_list_available_models(self, mock_session_manager, mock_poe_client):
        """Test the list_available_models tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test list available models
        response = client.call("list_available_models", {})
        
        # Check response
        self.assertIn("models", response)
        self.assertEqual(len(response["models"]), 3)
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_get_server_info(self, mock_session_manager, mock_poe_client):
        """Test the get_server_info tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test get server info
        response = client.call("get_server_info", {})
        
        # Check response
        self.assertIn("name", response)
        self.assertIn("version", response)
        self.assertIn("claude_compatible", response)
    
    def test_claude_compat_format_thinking(self):
        """Test the Claude compatibility format_thinking_protocol function."""
        # Test with thinking enabled
        prompt = "What is the capital of France?"
        thinking = {
            "thinking_enabled": True,
            "thinking_depth": 2
        }
        
        formatted_prompt = format_thinking_protocol(prompt, thinking)
        
        # Check that the formatted prompt contains the thinking protocol
        self.assertIn("<thinking>", formatted_prompt)
        self.assertIn("</thinking>", formatted_prompt)
        
        # Test with thinking disabled
        prompt = "What is the capital of France?"
        thinking = None
        
        formatted_prompt = format_thinking_protocol(prompt, thinking)
        
        # Check that the formatted prompt does not contain the thinking protocol
        self.assertNotIn("<thinking>", formatted_prompt)
        self.assertNotIn("</thinking>", formatted_prompt)
    
    def test_claude_compat_process_response(self):
        """Test the Claude compatibility process_claude_response function."""
        # Test with thinking in response
        response = """<thinking>
        Paris is the capital of France.
        It is located in Western Europe.
        </thinking>
        
        The capital of France is Paris."""
        
        processed_response = process_claude_response(response)
        
        # Check that the thinking protocol is removed
        self.assertNotIn("<thinking>", processed_response)
        self.assertNotIn("</thinking>", processed_response)
        self.assertEqual(processed_response.strip(), "The capital of France is Paris.")
        
        # Test without thinking in response
        response = "The capital of France is Paris."
        
        processed_response = process_claude_response(response)
        
        # Check that the response is unchanged
        self.assertEqual(processed_response.strip(), "The capital of France is Paris.")


class TestPoeProxyServerErrors(unittest.TestCase):
    """Test cases for error handling in the Poe Proxy MCP server."""

    def setUp(self):
        """Set up test environment."""
        # Load configuration
        self.config = get_config()
        
        # Create a mock PoeClient that raises exceptions
        self.mock_poe_client = MagicMock(spec=PoeClient)
        self.mock_poe_client.query_model.side_effect = Exception("Test error")
        self.mock_poe_client.query_model_with_file.side_effect = Exception("Test file error")
        
        # Create a session manager
        self.session_manager = SessionManager(expiry_minutes=10)
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_ask_poe_error(self, mock_session_manager, mock_poe_client):
        """Test error handling in the ask_poe tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test query with error
        response = client.call("ask_poe", {
            "bot": "GPT-3.5-Turbo",
            "prompt": "Hello, world!"
        })
        
        # Check response
        self.assertIn("error", response)
        self.assertIn("message", response)
    
    @patch('poe_server.poe_client', autospec=True)
    @patch('poe_server.session_manager', autospec=True)
    def test_ask_with_attachment_error(self, mock_session_manager, mock_poe_client):
        """Test error handling in the ask_with_attachment tool."""
        # Import the server module
        import poe_server
        
        # Replace the PoeClient and SessionManager with our mocks
        poe_server.poe_client = self.mock_poe_client
        poe_server.session_manager = self.session_manager
        
        # Create a client that points directly to the server
        client = Client(poe_server.mcp)
        
        # Test file sharing with error
        response = client.call("ask_with_attachment", {
            "bot": "GPT-4o",
            "prompt": "Analyze this file",
            "attachment_path": "non-existent-file.txt"
        })
        
        # Check response
        self.assertIn("error", response)
        self.assertIn("message", response)


if __name__ == "__main__":
    unittest.main()