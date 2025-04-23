"""
Poe API client wrapper for the Poe Proxy MCP server.

This module provides a clean interface for interacting with the Poe API,
handling authentication, streaming responses, and error handling.
"""
import os
import asyncio
import tempfile
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
import fastapi_poe as fp

from utils import (
    logger,
    AuthenticationError,
    PoeApiError,
    FileHandlingError,
    handle_exception,
)

from .claude_compat import (
    format_thinking_protocol,
    process_claude_response,
    handle_claude_error,
    is_claude_model,
)


class PoeClient:
    """
    Client for interacting with the Poe API.
    """
    
    def __init__(self, api_key: str, debug_mode: bool = False, claude_compatible: bool = False):
        """
        Initialize the Poe API client.
        
        Args:
            api_key (str): The Poe API key for authentication
            debug_mode (bool): Whether to enable debug logging
            claude_compatible (bool): Whether to enable Claude compatibility mode
        
        Raises:
            AuthenticationError: If the API key is invalid
        """
        if not api_key:
            raise AuthenticationError(
                "Poe API key is required. Get your API key from https://poe.com/api_key"
            )
        
        self.api_key = api_key
        self.debug_mode = debug_mode
        self.claude_compatible = claude_compatible
        
        if self.claude_compatible:
            logger.info("Claude compatibility mode enabled")
        
        logger.info("Poe API client initialized")
    
    async def query_model(
        self,
        bot_name: str,
        prompt: str,
        messages: Optional[List[fp.ProtocolMessage]] = None,
        stream_handler: Optional[callable] = None,
        thinking: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query a Poe model with a prompt.
        
        Args:
            bot_name (str): The name of the Poe bot to query
            prompt (str): The prompt to send to the bot
            messages (List[fp.ProtocolMessage], optional): Previous messages for context
            stream_handler (callable, optional): Function to handle streaming responses
            thinking (Dict[str, Any], optional): Parameters for Claude's thinking protocol
            
        Returns:
            Dict[str, Any]: The response from the bot
            
        Raises:
            PoeApiError: If there's an error from the Poe API
        """
        try:
            # Prepare messages
            if messages is None:
                messages = []
            
            # Add the new user message
            messages.append(fp.ProtocolMessage(role="user", content=prompt))
            
            if self.debug_mode:
                logger.debug(f"Querying bot '{bot_name}' with prompt: {prompt}")
                logger.debug(f"Message history length: {len(messages)}")
            
            # Handle Claude compatibility if needed
            is_claude = is_claude_model(bot_name)
            
            if is_claude and self.claude_compatible and thinking:
                formatted_thinking = format_thinking_protocol(thinking)
                logger.debug(f"Using Claude thinking protocol: {formatted_thinking}")
            else:
                formatted_thinking = None
            
            # Collect the full response
            full_response = ""
            try:
                async for partial in fp.get_bot_response(
                    messages=messages,
                    bot_name=bot_name,
                    api_key=self.api_key,
                ):
                    chunk_text = partial.text
                    
                    # Process Claude response if needed
                    if is_claude and self.claude_compatible:
                        chunk_text = process_claude_response(chunk_text)
                    
                    full_response += chunk_text
                    
                    # Call the stream handler if provided
                    if stream_handler:
                        await stream_handler(chunk_text)
            
            except Exception as e:
                # Handle Claude-specific errors
                if is_claude and self.claude_compatible:
                    error_info = handle_claude_error(e)
                    logger.warning(f"Claude error handled: {error_info['message']}")
                    
                    # If we have a partial response, return it with the error
                    if full_response:
                        return {
                            "text": full_response,
                            "bot": bot_name,
                            "error": error_info["error"],
                            "error_message": error_info["message"],
                        }
                    
                    # Otherwise, re-raise the error
                    raise PoeApiError(error_info["message"])
                
                # Re-raise other errors
                raise
            
            # Process the full response for Claude if needed
            if is_claude and self.claude_compatible:
                full_response = process_claude_response(full_response)
            
            if self.debug_mode:
                logger.debug(f"Received response from bot '{bot_name}' (length: {len(full_response)})")
            
            return {
                "text": full_response,
                "bot": bot_name,
            }
        
        except Exception as e:
            logger.error(f"Error querying Poe model: {str(e)}")
            raise PoeApiError(f"Error querying Poe model: {str(e)}")
    
    async def query_model_with_file(
        self,
        bot_name: str,
        prompt: str,
        file_path: str,
        messages: Optional[List[fp.ProtocolMessage]] = None,
        stream_handler: Optional[callable] = None,
        thinking: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query a Poe model with a prompt and a file.
        
        Args:
            bot_name (str): The name of the Poe bot to query
            prompt (str): The prompt to send to the bot
            file_path (str): Path to the file to include with the prompt
            messages (List[fp.ProtocolMessage], optional): Previous messages for context
            stream_handler (callable, optional): Function to handle streaming responses
            thinking (Dict[str, Any], optional): Parameters for Claude's thinking protocol
            
        Returns:
            Dict[str, Any]: The response from the bot
            
        Raises:
            FileHandlingError: If there's an issue with the file
            PoeApiError: If there's an error from the Poe API
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise FileHandlingError(f"File not found: {file_path}")
            
            # Prepare messages
            if messages is None:
                messages = []
            
            # Read the file content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # Try to decode as text, otherwise treat as binary
            try:
                file_text = file_content.decode("utf-8")
                combined_prompt = f"{prompt}\n\nFile content:\n{file_text}"
            except UnicodeDecodeError:
                # If it's not a text file, just use the original prompt
                combined_prompt = f"{prompt}\n\n[File attached: {os.path.basename(file_path)}]"
            
            if self.debug_mode:
                logger.debug(f"Querying bot '{bot_name}' with file: {file_path}")
                logger.debug(f"Message history length: {len(messages)}")
            
            # Handle Claude compatibility if needed
            is_claude = is_claude_model(bot_name)
            
            if is_claude and self.claude_compatible and thinking:
                formatted_thinking = format_thinking_protocol(thinking)
                logger.debug(f"Using Claude thinking protocol: {formatted_thinking}")
            else:
                formatted_thinking = None
            
            # Add the new user message with the file content
            messages.append(fp.ProtocolMessage(role="user", content=combined_prompt))
            
            # Collect the full response
            full_response = ""
            try:
                async for partial in fp.get_bot_response(
                    messages=messages,
                    bot_name=bot_name,
                    api_key=self.api_key,
                ):
                    chunk_text = partial.text
                    
                    # Process Claude response if needed
                    if is_claude and self.claude_compatible:
                        chunk_text = process_claude_response(chunk_text)
                    
                    full_response += chunk_text
                    
                    # Call the stream handler if provided
                    if stream_handler:
                        await stream_handler(chunk_text)
            
            except Exception as e:
                # Handle Claude-specific errors
                if is_claude and self.claude_compatible:
                    error_info = handle_claude_error(e)
                    logger.warning(f"Claude error handled: {error_info['message']}")
                    
                    # If we have a partial response, return it with the error
                    if full_response:
                        return {
                            "text": full_response,
                            "bot": bot_name,
                            "error": error_info["error"],
                            "error_message": error_info["message"],
                        }
                    
                    # Otherwise, re-raise the error
                    raise PoeApiError(error_info["message"])
                
                # Re-raise other errors
                raise
            
            # Process the full response for Claude if needed
            if is_claude and self.claude_compatible:
                full_response = process_claude_response(full_response)
            
            if self.debug_mode:
                logger.debug(f"Received response from bot '{bot_name}' with file (length: {len(full_response)})")
            
            return {
                "text": full_response,
                "bot": bot_name,
            }
        
        except FileHandlingError as e:
            logger.error(f"File handling error: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Error querying Poe model with file: {str(e)}")
            raise PoeApiError(f"Error querying Poe model with file: {str(e)}")
    
    @staticmethod
    def get_available_models() -> List[str]:
        """
        Get a list of available Poe models.
        
        Returns:
            List[str]: List of available model names
        """
        # These are the standard models available on Poe
        # This list may need to be updated as Poe adds or removes models
        return [
            "GPT-3.5-Turbo",
            "GPT-4",
            "GPT-4o",
            "Claude-3-Opus-200k",
            "Claude-3-Sonnet-7k",
            "Claude-3-Haiku-3k",
            "Claude-2-100k",
            "Gemini-Pro",
            "Llama-3-70b",
            "Llama-3-8b",
            "Mistral-7B",
            "Mistral-Large",
            "Perplexity-Online",
        ]
    
    @staticmethod
    def get_model_info(model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific Poe model.
        
        Args:
            model_name (str): The name of the model
            
        Returns:
            Dict[str, Any]: Information about the model
            
        Raises:
            ValueError: If the model is not recognized
        """
        model_info = {
            "GPT-3.5-Turbo": {
                "description": "OpenAI's GPT-3.5 Turbo model",
                "context_length": 16000,
                "supports_images": True,
            },
            "GPT-4": {
                "description": "OpenAI's GPT-4 model",
                "context_length": 32000,
                "supports_images": True,
            },
            "GPT-4o": {
                "description": "OpenAI's GPT-4o model",
                "context_length": 128000,
                "supports_images": True,
            },
            "Claude-3-Opus-200k": {
                "description": "Anthropic's Claude 3 Opus model with 200k context",
                "context_length": 200000,
                "supports_images": True,
            },
            "Claude-3-Sonnet-7k": {
                "description": "Anthropic's Claude 3 Sonnet model with 7k context",
                "context_length": 7000,
                "supports_images": True,
            },
            "Claude-3-Haiku-3k": {
                "description": "Anthropic's Claude 3 Haiku model with 3k context",
                "context_length": 3000,
                "supports_images": True,
            },
            "Claude-2-100k": {
                "description": "Anthropic's Claude 2 model with 100k context",
                "context_length": 100000,
                "supports_images": False,
            },
            "Gemini-Pro": {
                "description": "Google's Gemini Pro model",
                "context_length": 32000,
                "supports_images": True,
            },
            "Llama-3-70b": {
                "description": "Meta's Llama 3 70B model",
                "context_length": 8000,
                "supports_images": False,
            },
            "Llama-3-8b": {
                "description": "Meta's Llama 3 8B model",
                "context_length": 8000,
                "supports_images": False,
            },
            "Mistral-7B": {
                "description": "Mistral AI's 7B model",
                "context_length": 8000,
                "supports_images": False,
            },
            "Mistral-Large": {
                "description": "Mistral AI's Large model",
                "context_length": 32000,
                "supports_images": True,
            },
            "Perplexity-Online": {
                "description": "Perplexity's online search-augmented model",
                "context_length": 8000,
                "supports_images": False,
            },
        }
        
        if model_name not in model_info:
            raise ValueError(f"Unknown model: {model_name}")
        
        return model_info[model_name]