#!/usr/bin/env python3
"""
Poe API Client (SDK-Compatible Version)

A client for the Poe API that provides methods for querying models and handling file attachments.
This implementation is compatible with the official Python MCP SDK and includes enhanced
support for Claude's thinking protocol.
"""
import os
import json
import asyncio
import tempfile
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from pathlib import Path

import httpx
from loguru import logger

# Import Claude compatibility module
from claude_compat_v2 import (
    ClaudeThinkingProtocol,
    is_claude_model,
    format_thinking_protocol,
    process_claude_response,
    handle_claude_error,
)

# Import file utilities
from file_utils import (
    validate_file,
    is_text_file,
    read_file_content,
    create_temp_file,
)


class PoeApiError(Exception):
    """Exception raised for errors in the Poe API."""
    pass


class AuthenticationError(PoeApiError):
    """Exception raised for authentication errors."""
    pass


class FileHandlingError(PoeApiError):
    """Exception raised for file handling errors."""
    pass


class PoeClient:
    """
    A client for the Poe API that provides methods for querying models and handling file attachments.
    
    This client is designed to be compatible with the official Python MCP SDK and includes
    enhanced support for Claude's thinking protocol.
    """
    
    def __init__(
        self,
        api_key: str,
        debug_mode: bool = False,
        claude_compatible: bool = True,
        timeout: int = 60,
    ):
        """
        Initialize the Poe API client.
        
        Args:
            api_key: The Poe API key
            debug_mode: Whether to enable debug mode
            claude_compatible: Whether to enable Claude compatibility
            timeout: Timeout for API requests in seconds
        """
        self.api_key = api_key
        self.debug_mode = debug_mode
        self.claude_compatible = claude_compatible
        self.timeout = timeout
        
        # Initialize Claude thinking protocol handler
        self.claude_thinking = ClaudeThinkingProtocol(
            enabled=claude_compatible,
            template="{{thinking}}",
            include_in_response=False,
        )
        
        # Initialize httpx client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        
        # Cache for available models
        self._available_models = None
        
        if debug_mode:
            logger.info("Initialized Poe API client")
            logger.info(f"Claude compatibility: {claude_compatible}")
    
    async def close(self):
        """Close the httpx client."""
        await self.client.aclose()
    
    async def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """
        Get a list of available models from the Poe API.
        
        Args:
            force_refresh: Whether to force a refresh of the cached models
            
        Returns:
            List of available model names
        """
        if self._available_models is None or force_refresh:
            try:
                response = await self.client.get("https://api.poe.com/api/available_models")
                response.raise_for_status()
                
                data = response.json()
                self._available_models = [model["slug"] for model in data["models"]]
                
                if self.debug_mode:
                    logger.info(f"Available models: {self._available_models}")
                
                return self._available_models
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                else:
                    raise PoeApiError(f"HTTP error: {e}")
            
            except Exception as e:
                raise PoeApiError(f"Error getting available models: {e}")
        
        return self._available_models
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model_name: The name of the model
            
        Returns:
            Dictionary with model information
        """
        try:
            # Ensure we have the available models
            models = await self.get_available_models()
            
            # Find the model in the available models
            response = await self.client.get("https://api.poe.com/api/available_models")
            response.raise_for_status()
            
            data = response.json()
            
            for model in data["models"]:
                if model["slug"].lower() == model_name.lower():
                    return {
                        "name": model["slug"],
                        "display_name": model.get("display_name", model["slug"]),
                        "description": model.get("description", ""),
                        "context_length": model.get("context_length", 4000),
                        "supports_images": model.get("supports_images", False),
                    }
            
            raise ValueError(f"Model {model_name} not found")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            else:
                raise PoeApiError(f"HTTP error: {e}")
        
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise PoeApiError(f"Error getting model info: {e}")
    
    async def query_model(
        self,
        bot_name: str,
        prompt: str,
        messages: Optional[List[Dict[str, str]]] = None,
        stream_handler: Optional[Callable[[str], Awaitable[None]]] = None,
        thinking: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Query a Poe model with a prompt.
        
        Args:
            bot_name: The name of the bot to query
            prompt: The prompt to send to the bot
            messages: Optional list of previous messages
            stream_handler: Optional function to handle streaming responses
            thinking: Optional parameters for Claude's thinking protocol
            
        Returns:
            Dictionary with the response text
        """
        try:
            # Format prompt with thinking protocol if applicable
            formatted_prompt = prompt
            if self.claude_compatible and is_claude_model(bot_name):
                # Use the thinking protocol handler
                if thinking is not None:
                    # Update the thinking protocol handler with the provided parameters
                    self.claude_thinking.enabled = thinking.get("enabled", True)
                    if "template" in thinking:
                        self.claude_thinking.template = thinking["template"]
                    if "include_in_response" in thinking:
                        self.claude_thinking.include_in_response = thinking["include_in_response"]
                
                formatted_prompt = self.claude_thinking.format_prompt(prompt, bot_name)
                
                if self.debug_mode:
                    logger.debug(f"Formatted prompt with thinking protocol: {formatted_prompt}")
            
            # Prepare the request payload
            payload = {
                "bot": bot_name,
                "message": formatted_prompt,
            }
            
            # Add previous messages if provided
            if messages:
                payload["conversation_id"] = "mcp_session"
                payload["message_history"] = messages
            
            # Make the API request
            response = await self.client.post(
                "https://api.poe.com/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            response_text = data.get("response", "")
            
            # Process the response with thinking protocol if applicable
            if self.claude_compatible and is_claude_model(bot_name):
                processed = self.claude_thinking.process_response(response_text)
                return {
                    "text": processed["response"],
                    "thinking": processed.get("thinking", ""),
                }
            
            return {"text": response_text}
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            else:
                error_text = f"HTTP error: {e}"
                if self.claude_compatible and is_claude_model(bot_name):
                    # Try fallback without thinking protocol
                    async def fallback_query(prompt_text, disabled_thinking):
                        return await self.query_model(
                            bot_name=bot_name,
                            prompt=prompt_text,
                            messages=messages,
                            stream_handler=None,  # Disable streaming for fallback
                            thinking=disabled_thinking,
                        )
                    
                    return await handle_claude_error(
                        error=e,
                        fallback_handler=fallback_query,
                        prompt=prompt,
                        model_name=bot_name,
                        thinking=thinking,
                    )
                
                raise PoeApiError(error_text)
        
        except Exception as e:
            error_text = f"Error querying model: {e}"
            if self.claude_compatible and is_claude_model(bot_name):
                # Try fallback without thinking protocol
                async def fallback_query(prompt_text, disabled_thinking):
                    return await self.query_model(
                        bot_name=bot_name,
                        prompt=prompt_text,
                        messages=messages,
                        stream_handler=None,  # Disable streaming for fallback
                        thinking=disabled_thinking,
                    )
                
                return await handle_claude_error(
                    error=e,
                    fallback_handler=fallback_query,
                    prompt=prompt,
                    model_name=bot_name,
                    thinking=thinking,
                )
            
            raise PoeApiError(error_text)
    
    async def query_model_with_file(
        self,
        bot_name: str,
        prompt: str,
        file_path: str,
        messages: Optional[List[Dict[str, str]]] = None,
        stream_handler: Optional[Callable[[str], Awaitable[None]]] = None,
        thinking: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Query a Poe model with a prompt and a file attachment.
        
        Args:
            bot_name: The name of the bot to query
            prompt: The prompt to send to the bot
            file_path: Path to the file to attach
            messages: Optional list of previous messages
            stream_handler: Optional function to handle streaming responses
            thinking: Optional parameters for Claude's thinking protocol
            
        Returns:
            Dictionary with the response text
        """
        try:
            # Validate the file
            validate_file(file_path)
            
            # Check if it's a text file
            if is_text_file(file_path):
                # For text files, we can include the content in the prompt
                file_content = read_file_content(file_path)
                file_name = os.path.basename(file_path)
                
                # Format the prompt with the file content
                file_prompt = f"{prompt}\n\nFile: {file_name}\n\n```\n{file_content}\n```"
                
                # Query the model with the formatted prompt
                return await self.query_model(
                    bot_name=bot_name,
                    prompt=file_prompt,
                    messages=messages,
                    stream_handler=stream_handler,
                    thinking=thinking,
                )
            
            # For non-text files, we need to use the file attachment API
            # This is a placeholder for future implementation
            raise FileHandlingError("Non-text file attachments are not yet supported")
        
        except Exception as e:
            if isinstance(e, FileHandlingError):
                raise
            
            error_text = f"Error querying model with file: {e}"
            if self.claude_compatible and is_claude_model(bot_name):
                # Try fallback without thinking protocol
                async def fallback_query(prompt_text, disabled_thinking):
                    return await self.query_model_with_file(
                        bot_name=bot_name,
                        prompt=prompt_text,
                        file_path=file_path,
                        messages=messages,
                        stream_handler=None,  # Disable streaming for fallback
                        thinking=disabled_thinking,
                    )
                
                return await handle_claude_error(
                    error=e,
                    fallback_handler=fallback_query,
                    prompt=prompt,
                    model_name=bot_name,
                    thinking=thinking,
                )
            
            raise PoeApiError(error_text)


class SessionManager:
    """
    A class to manage sessions for the Poe API client.
    
    This class provides methods for creating, retrieving, updating, and deleting sessions,
    as well as managing session expiry.
    """
    
    def __init__(self, expiry_minutes: int = 60):
        """
        Initialize the session manager.
        
        Args:
            expiry_minutes: The number of minutes after which a session expires
        """
        self.sessions = {}
        self.expiry_minutes = expiry_minutes
        self.expiry_seconds = expiry_minutes * 60
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> str:
        """
        Get an existing session or create a new one.
        
        Args:
            session_id: Optional session ID to retrieve
            
        Returns:
            The session ID
        """
        if session_id and session_id in self.sessions:
            # Update the last access time
            self.sessions[session_id]["last_access"] = asyncio.get_event_loop().time()
            return session_id
        
        # Create a new session ID
        import uuid
        new_session_id = str(uuid.uuid4())
        
        # Create a new session
        self.sessions[new_session_id] = {
            "messages": [],
            "last_access": asyncio.get_event_loop().time(),
        }
        
        return new_session_id
    
    def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get the messages for a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            List of messages
        """
        if session_id in self.sessions:
            # Update the last access time
            self.sessions[session_id]["last_access"] = asyncio.get_event_loop().time()
            return self.sessions[session_id]["messages"]
        
        return []
    
    def update_session(
        self,
        session_id: str,
        user_message: str,
        bot_message: str,
    ) -> bool:
        """
        Update a session with new messages.
        
        Args:
            session_id: The session ID
            user_message: The user's message
            bot_message: The bot's response
            
        Returns:
            True if the session was updated, False otherwise
        """
        if session_id in self.sessions:
            # Add the messages to the session
            self.sessions[session_id]["messages"].append({
                "role": "user",
                "content": user_message,
            })
            self.sessions[session_id]["messages"].append({
                "role": "assistant",
                "content": bot_message,
            })
            
            # Update the last access time
            self.sessions[session_id]["last_access"] = asyncio.get_event_loop().time()
            
            return True
        
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID
            
        Returns:
            True if the session was deleted, False otherwise
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            The number of sessions that were cleaned up
        """
        current_time = asyncio.get_event_loop().time()
        expired_sessions = []
        
        # Find expired sessions
        for session_id, session in self.sessions.items():
            if current_time - session["last_access"] > self.expiry_seconds:
                expired_sessions.append(session_id)
        
        # Delete expired sessions
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        return len(expired_sessions)