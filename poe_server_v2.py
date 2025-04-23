#!/usr/bin/env python3
"""
Poe Proxy MCP Server (SDK-Compatible Version)

A FastMCP server that proxies the Poe.com API, exposing tools for querying Poe models
and sharing files. This implementation follows the structure of the official Python MCP SDK.
"""
import os
import asyncio
import tempfile
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
from pydantic import BaseModel, Field

# Import from the official MCP SDK
try:
    from mcp.server.fastmcp import FastMCP
    from mcp.shared.context import RequestContext
except ImportError:
    raise ImportError(
        "The mcp package is not installed. Please install it with: pip install mcp"
    )

# Import our utility modules
from utils import (
    setup_logging,
    get_config,
    PoeProxyError,
    AuthenticationError,
    PoeApiError,
    FileHandlingError,
    handle_exception,
)

from poe_client import (
    PoeClient,
    SessionManager,
    validate_file,
    is_text_file,
    read_file_content,
    create_temp_file,
    format_thinking_protocol,
    process_claude_response,
    handle_claude_error,
    is_claude_model,
)

# Initialize logging and configuration
config = get_config()
logger = setup_logging(config.debug_mode)

# Create FastMCP server
mcp = FastMCP("Poe Proxy MCP Server")

# Initialize Poe API client and session manager
poe_client = PoeClient(
    api_key=config.poe_api_key,
    debug_mode=config.debug_mode,
    claude_compatible=config.claude_compatible,
)
session_manager = SessionManager(expiry_minutes=config.session_expiry_minutes)


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
    thinking: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for Claude's thinking protocol"
    )


class QueryResponse(BaseModel):
    """Response model for Poe queries."""
    
    text: str = Field(
        description="The response text from the bot"
    )
    session_id: str = Field(
        description="Session ID for maintaining conversation context"
    )


@mcp.tool()
async def ask_poe(
    bot: str,
    prompt: str,
    session_id: Optional[str] = None,
    thinking: Optional[Dict[str, Any]] = None,
    context: Optional[RequestContext] = None,
) -> Dict[str, str]:
    """
    Ask a question to a Poe bot.
    
    Args:
        bot: The bot to ask (o3, claude, gemini, perplexity, or gpt)
        prompt: The text prompt to send to the bot
        thinking: Optional parameters for Claude's thinking protocol
        session_id: Optional session ID for maintaining conversation context
        context: Request context (provided by MCP)
        
    Returns:
        Response from the bot and session information
    """
    try:
        # Get or create session
        current_session_id = session_manager.get_or_create_session(session_id)
        
        # Get messages from session
        messages = session_manager.get_messages(current_session_id)
        
        # Define stream handler for progress updates
        async def stream_handler(text: str):
            if context and hasattr(context, "report_progress"):
                # Use the context to report progress if available
                await context.report_progress(50)  # Report 50% progress
            elif hasattr(mcp, "yield_progress"):
                # Fall back to yield_progress if context is not available
                await mcp.yield_progress({"text": text})
        
        # Query the Poe model
        response = await poe_client.query_model(
            bot_name=bot,
            prompt=prompt,
            messages=messages,
            stream_handler=stream_handler,
            thinking=thinking,
        )
        
        # Update session with the new messages
        session_manager.update_session(
            session_id=current_session_id,
            user_message=prompt,
            bot_message=response["text"],
        )
        
        # Check if there was an error but we still got a partial response
        if "error" in response:
            return {
                "text": response["text"],
                "session_id": current_session_id,
                "warning": response["error_message"],
            }
        
        return {
            "text": response["text"],
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
    context: Optional[RequestContext] = None,
) -> Dict[str, str]:
    """
    Ask a question to a Poe bot with a file attachment.
    
    Args:
        bot: The bot to ask (o3, claude, gemini, perplexity, or gpt)
        prompt: The text prompt to send to the bot
        attachment_path: Path to the file to attach
        thinking: Optional parameters for Claude's thinking protocol
        session_id: Optional session ID for maintaining conversation context
        context: Request context (provided by MCP)
        
    Returns:
        Response from the bot and session information
    """
    try:
        # Validate file
        validate_file(attachment_path, max_size_mb=config.max_file_size_mb)
        
        # Get or create session
        current_session_id = session_manager.get_or_create_session(session_id)
        
        # Get messages from session
        messages = session_manager.get_messages(current_session_id)
        
        # Define stream handler for progress updates
        async def stream_handler(text: str):
            if context and hasattr(context, "report_progress"):
                # Use the context to report progress if available
                await context.report_progress(50)  # Report 50% progress
            elif hasattr(mcp, "yield_progress"):
                # Fall back to yield_progress if context is not available
                await mcp.yield_progress({"text": text})
        
        # Query the Poe model with the file
        response = await poe_client.query_model_with_file(
            bot_name=bot,
            prompt=prompt,
            file_path=attachment_path,
            messages=messages,
            stream_handler=stream_handler,
            thinking=thinking,
        )
        
        # Update session with the new messages
        session_manager.update_session(
            session_id=current_session_id,
            user_message=f"{prompt} [File: {os.path.basename(attachment_path)}]",
            bot_message=response["text"],
        )
        
        # Check if there was an error but we still got a partial response
        if "error" in response:
            return {
                "text": response["text"],
                "session_id": current_session_id,
                "warning": response["error_message"],
            }
        
        return {
            "text": response["text"],
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
def clear_session(
    session_id: str,
    context: Optional[RequestContext] = None,
) -> Dict[str, str]:
    """
    Clear a session's conversation history.
    
    Args:
        session_id: The session ID to clear
        context: Request context (provided by MCP)
        
    Returns:
        Status information
    """
    try:
        success = session_manager.delete_session(session_id)
        
        if success:
            return {"status": "success", "message": f"Session {session_id} cleared"}
        else:
            return {"status": "error", "message": f"Session {session_id} not found"}
    
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "status": "error",
            "message": error_info["message"],
        }


@mcp.tool()
def list_available_models(
    context: Optional[RequestContext] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    List available Poe models and their capabilities.
    
    Args:
        context: Request context (provided by MCP)
        
    Returns:
        Dictionary with list of available models and their information
    """
    try:
        models = []
        
        for model_name in poe_client.get_available_models():
            try:
                model_info = poe_client.get_model_info(model_name)
                models.append({
                    "name": model_name,
                    "description": model_info["description"],
                    "context_length": model_info["context_length"],
                    "supports_images": model_info["supports_images"],
                    "is_claude": is_claude_model(model_name),
                })
            except ValueError:
                # Skip models with missing info
                continue
        
        return {"models": models}
    
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "error": error_info["error"],
            "message": error_info["message"],
            "models": [],
        }


@mcp.tool()
def get_server_info(
    context: Optional[RequestContext] = None,
) -> Dict[str, Any]:
    """
    Get information about the server configuration.
    
    Args:
        context: Request context (provided by MCP)
        
    Returns:
        Dictionary with server information
    """
    try:
        return {
            "name": "Poe Proxy MCP Server",
            "version": "0.2.0",  # Updated version for SDK compatibility
            "claude_compatible": config.claude_compatible,
            "debug_mode": config.debug_mode,
            "max_file_size_mb": config.max_file_size_mb,
            "session_expiry_minutes": config.session_expiry_minutes,
            "active_sessions": len(session_manager.sessions),
            "sdk_compatible": True,
        }
    
    except Exception as e:
        error_info = handle_exception(e)
        return {
            "error": error_info["error"],
            "message": error_info["message"],
        }


# Periodic task to clean up expired sessions
async def cleanup_sessions_task():
    """Periodically clean up expired sessions."""
    while True:
        try:
            # Clean up expired sessions
            num_cleaned = session_manager.cleanup_expired_sessions()
            
            if num_cleaned > 0:
                logger.info(f"Cleaned up {num_cleaned} expired sessions")
            
            # Sleep for 15 minutes
            await asyncio.sleep(15 * 60)
        
        except Exception as e:
            logger.error(f"Error in cleanup_sessions_task: {str(e)}")
            # Sleep for 1 minute before retrying
            await asyncio.sleep(60)


# Start the cleanup task when the server starts
@mcp.on_startup
async def startup():
    """Start background tasks when the server starts."""
    logger.info("Starting Poe Proxy MCP Server (SDK-Compatible Version)")
    logger.info(f"Claude compatibility mode: {config.claude_compatible}")
    
    # Start the session cleanup task
    asyncio.create_task(cleanup_sessions_task())


def main():
    """Entry point for the console script."""
    logger.info("Starting Poe Proxy MCP Server with STDIO transport")
    mcp.run()


if __name__ == "__main__":
    # Run the MCP server
    main()