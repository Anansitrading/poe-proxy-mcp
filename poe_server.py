#!/usr/bin/env python3
"""
Poe Proxy MCP Server

A FastMCP server that proxies the Poe.com API, exposing tools for querying Poe models
and sharing files. The server supports both STDIO and SSE transports.
"""
import os
import asyncio
import tempfile
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
from fastmcp import FastMCP
import fastapi_poe as fp
from pydantic import BaseModel, Field

from utils import (
    setup_logging,
    get_config,
    PoeProxyError,
    AuthenticationError,
    PoeApiError,
    FileHandlingError,
    handle_exception,
)

# Initialize logging
config = get_config()
logger = setup_logging(config.debug_mode)

# Create FastMCP server
mcp = FastMCP("Poe Proxy MCP Server")


# Define models for the MCP tools
class QueryRequest(BaseModel):
    """Request model for querying Poe models."""
    
    bot: str = Field(
        description="The Poe bot to query (e.g., 'GPT-3.5-Turbo', 'Claude-3-Opus')"
    )
    prompt: str = Field(
        description="The prompt to send to the bot"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for maintaining conversation context"
    )
    thinking: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for Claude's thinking protocol"
    )


class FileShareRequest(BaseModel):
    """Request model for sharing files with Poe models."""
    
    bot: str = Field(
        description="The Poe bot to share the file with"
    )
    prompt: str = Field(
        description="The prompt to send along with the file"
    )
    file_path: str = Field(
        description="Path to the file to share"
    )
    mime_type: Optional[str] = Field(
        default=None,
        description="MIME type of the file (if not provided, will be inferred)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for maintaining conversation context"
    )


class QueryResponse(BaseModel):
    """Response model for Poe queries."""
    
    text: str = Field(
        description="The response text from the bot"
    )
    session_id: str = Field(
        description="Session ID for maintaining conversation context"
    )


# Session storage
sessions: Dict[str, List[fp.ProtocolMessage]] = {}


def _generate_session_id() -> str:
    """Generate a unique session ID."""
    import uuid
    return str(uuid.uuid4())


def _get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get an existing session or create a new one."""
    if session_id and session_id in sessions:
        return session_id
    
    new_session_id = _generate_session_id()
    sessions[new_session_id] = []
    return new_session_id


def _update_session(session_id: str, user_message: str, bot_message: str) -> None:
    """Update a session with new messages."""
    if session_id not in sessions:
        sessions[session_id] = []
    
    sessions[session_id].append(fp.ProtocolMessage(role="user", content=user_message))
    sessions[session_id].append(fp.ProtocolMessage(role="assistant", content=bot_message))


@mcp.tool()
async def ask_poe(
    bot: str,
    prompt: str,
    session_id: Optional[str] = None,
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Ask a question to a Poe bot.
    
    Args:
        bot: The bot to ask (o3, claude, gemini, perplexity, or gpt)
        prompt: The text prompt to send to the bot
        thinking: Optional parameters for Claude's thinking protocol
        session_id: Optional session ID for maintaining conversation context
        
    Returns:
        Response from the bot and session information
    """
    try:
        # Get or create session
        current_session_id = _get_or_create_session(session_id)
        
        # Prepare messages
        messages = []
        if current_session_id in sessions:
            messages = sessions[current_session_id].copy()
        
        # Add the new user message
        messages.append(fp.ProtocolMessage(role="user", content=prompt))
        
        # Collect the full response
        full_response = ""
        async for partial in fp.get_bot_response(
            messages=messages,
            bot_name=bot,
            api_key=config.poe_api_key,
        ):
            full_response += partial.text
            
            # Yield progress updates if using streaming
            if hasattr(mcp, "yield_progress"):
                await mcp.yield_progress({"text": partial.text})
        
        # Update session with the new messages
        _update_session(current_session_id, prompt, full_response)
        
        return {
            "text": full_response,
            "session_id": current_session_id,
        }
    
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "error": error_info["error"],
            "message": error_info["message"],
            "session_id": session_id or "",
        }


@mcp.tool()
async def ask_with_attachment(
    bot: str,
    prompt: str,
    attachment_path: str,
    session_id: Optional[str] = None,
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Ask a question to a Poe bot with a file attachment.
    
    Args:
        bot: The bot to ask (o3, claude, gemini, perplexity, or gpt)
        prompt: The text prompt to send to the bot
        attachment_path: Path to the file to attach
        thinking: Optional parameters for Claude's thinking protocol
        session_id: Optional session ID for maintaining conversation context
        
    Returns:
        Response from the bot and session information
    """
    try:
        # Validate file exists
        if not os.path.exists(attachment_path):
            raise FileHandlingError(f"File not found: {attachment_path}")
        
        # Check file size
        file_size_mb = os.path.getsize(attachment_path) / (1024 * 1024)
        if file_size_mb > config.max_file_size_mb:
            raise FileHandlingError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size "
                f"({config.max_file_size_mb} MB)"
            )
        
        # Get or create session
        current_session_id = _get_or_create_session(session_id)
        
        # Prepare messages
        messages = []
        if current_session_id in sessions:
            messages = sessions[current_session_id].copy()
        
        # Add the new user message with attachment
        # Note: This is a placeholder as fastapi_poe doesn't directly support file attachments
        # In a real implementation, you would need to handle file uploads differently
        with open(attachment_path, "rb") as f:
            file_content = f.read()
            
        # For now, we'll just include the file content as text if it's a text file
        # In a real implementation, you would use the appropriate API for file uploads
        try:
            file_text = file_content.decode("utf-8")
            combined_prompt = f"{prompt}\n\nFile content:\n{file_text}"
        except UnicodeDecodeError:
            # If it's not a text file, just use the original prompt
            combined_prompt = f"{prompt}\n\n[File attached: {os.path.basename(attachment_path)}]"
        
        messages.append(fp.ProtocolMessage(role="user", content=combined_prompt))
        
        # Collect the full response
        full_response = ""
        async for partial in fp.get_bot_response(
            messages=messages,
            bot_name=bot,
            api_key=config.poe_api_key,
        ):
            full_response += partial.text
            
            # Yield progress updates if using streaming
            if hasattr(mcp, "yield_progress"):
                await mcp.yield_progress({"text": partial.text})
        
        # Update session with the new messages
        _update_session(current_session_id, combined_prompt, full_response)
        
        return {
            "text": full_response,
            "session_id": current_session_id,
        }
    
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "error": error_info["error"],
            "message": error_info["message"],
            "session_id": session_id or "",
        }


@mcp.tool()
def clear_session(session_id: str) -> Dict[str, str]:
    """
    Clear a session's conversation history.
    
    Args:
        session_id: The session ID to clear
        
    Returns:
        Status information
    """
    try:
        if session_id in sessions:
            sessions.pop(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        else:
            return {"status": "error", "message": f"Session {session_id} not found"}
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "status": "error",
            "message": error_info["message"],
        }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()