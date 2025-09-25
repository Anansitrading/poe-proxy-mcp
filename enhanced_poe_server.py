#!/usr/bin/env python3
"""
Enhanced POE MCP Server with Warp Agent Integration

This extends the original POE MCP server with native Warp terminal integration,
allowing POE model responses to directly drive terminal actions.
"""
import os
import asyncio
import tempfile
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

# Use fastmcp instead of the official SDK for now
from fastmcp import FastMCP

# Import utilities
from utils import (
    setup_logging,
    get_config,
    handle_exception,
    FileHandlingError
)

# Import our Warp agent tools
from warp_agent_tools import (
    WarpActionResult,
    execute_terminal_command,
    create_file_from_response,
    open_file_in_editor,
    parse_and_execute_actions,
    format_action_results
)

from pydantic import BaseModel, Field


class EnhancedQueryRequest(BaseModel):
    """Enhanced request model for POE queries with agent actions."""
    
    bot: str = Field(description="The Poe bot to query")
    prompt: str = Field(description="The prompt to send to the bot")
    session_id: Optional[str] = Field(default=None, description="Session ID for context")
    thinking: Optional[Dict[str, Any]] = Field(default=None, description="Claude thinking protocol params")
    execute_actions: bool = Field(default=True, description="Whether to execute detected actions")
    working_directory: Optional[str] = Field(default=None, description="Working directory for commands")


class AgentQueryResponse(BaseModel):
    """Response model for agent-enhanced queries."""
    
    text: str = Field(description="The response text from the bot")
    session_id: str = Field(description="Session ID for maintaining context")
    actions_executed: List[WarpActionResult] = Field(default=[], description="Actions performed")
    action_summary: Optional[str] = Field(default=None, description="Summary of actions taken")


@mcp.tool()
async def ask_poe_with_actions(
    bot: str,
    prompt: str,
    session_id: Optional[str] = None,
    thinking: Optional[Dict[str, Any]] = None,
    execute_actions: bool = True,
    working_directory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask a POE bot and automatically execute any detected actions in the response.
    
    This tool extends the basic ask_poe functionality by:
    1. Getting the response from the POE model
    2. Parsing the response for action directives (file creation, commands, etc.)
    3. Executing those actions in the Warp terminal
    4. Returning both the response and action results
    
    Args:
        bot: The bot to ask (claude, gpt, etc.)
        prompt: The text prompt to send
        session_id: Optional session ID for context
        thinking: Optional Claude thinking protocol parameters
        execute_actions: Whether to automatically execute detected actions
        working_directory: Working directory for any commands
        
    Returns:
        Enhanced response with both text and action results
    """
    try:
        # First, get the normal POE response
        logger.info(f"Querying bot '{bot}' with actions enabled: {execute_actions}")
        
        poe_response = await ask_poe(
            bot=bot,
            prompt=prompt,
            session_id=session_id,
            thinking=thinking
        )
        
        # If there was an error in the POE response, return it as-is
        if "error" in poe_response:
            return poe_response
        
        response_text = poe_response["text"]
        current_session_id = poe_response["session_id"]
        
        # Initialize action results
        action_results = []
        action_summary = None
        
        # Parse and execute actions if enabled
        if execute_actions:
            logger.debug("Parsing response for actionable directives")
            
            # Set working directory to current directory if not specified
            if working_directory is None:
                working_directory = os.getcwd()
            
            # Parse and execute actions
            action_results = await parse_and_execute_actions(
                poe_response=response_text,
                working_directory=working_directory
            )
            
            # Generate action summary
            if action_results:
                action_summary = format_action_results(action_results)
                logger.info(f"Executed {len(action_results)} actions from POE response")
            else:
                logger.debug("No actionable directives found in response")
        
        # Return enhanced response
        return {
            "text": response_text,
            "session_id": current_session_id,
            "actions_executed": [result.dict() for result in action_results],
            "action_summary": action_summary,
            "execute_actions_enabled": execute_actions,
        }
        
    except Exception as e:
        logger.error(f"Error in ask_poe_with_actions: {str(e)}")
        return {
            "error": "agent_query_error",
            "message": str(e),
            "session_id": session_id or "",
            "actions_executed": [],
        }


@mcp.tool()
async def ask_with_attachment_and_actions(
    bot: str,
    prompt: str,
    attachment_path: str,
    session_id: Optional[str] = None,
    thinking: Optional[Dict[str, Any]] = None,
    execute_actions: bool = True,
    working_directory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask a POE bot with file attachment and execute detected actions.
    
    This combines file sharing with automatic action execution, perfect for:
    - Code analysis and modification
    - Configuration file updates
    - Documentation generation and filing
    
    Args:
        bot: The bot to ask
        prompt: The text prompt
        attachment_path: Path to file to attach
        session_id: Optional session ID for context
        thinking: Optional Claude thinking protocol parameters
        execute_actions: Whether to execute detected actions
        working_directory: Working directory for commands
        
    Returns:
        Enhanced response with both text and action results
    """
    try:
        logger.info(f"Querying bot '{bot}' with attachment and actions enabled: {execute_actions}")
        
        # First, get the normal POE response with attachment
        poe_response = await ask_with_attachment(
            bot=bot,
            prompt=prompt,
            attachment_path=attachment_path,
            session_id=session_id,
            thinking=thinking
        )
        
        # If there was an error in the POE response, return it as-is
        if "error" in poe_response:
            return poe_response
        
        response_text = poe_response["text"]
        current_session_id = poe_response["session_id"]
        
        # Initialize action results
        action_results = []
        action_summary = None
        
        # Parse and execute actions if enabled
        if execute_actions:
            logger.debug("Parsing response for actionable directives")
            
            # Set working directory to attachment file's directory if not specified
            if working_directory is None:
                working_directory = os.path.dirname(os.path.abspath(attachment_path))
            
            # Parse and execute actions
            action_results = await parse_and_execute_actions(
                poe_response=response_text,
                working_directory=working_directory
            )
            
            # Generate action summary
            if action_results:
                action_summary = format_action_results(action_results)
                logger.info(f"Executed {len(action_results)} actions from POE response")
        
        # Return enhanced response
        return {
            "text": response_text,
            "session_id": current_session_id,
            "actions_executed": [result.dict() for result in action_results],
            "action_summary": action_summary,
            "execute_actions_enabled": execute_actions,
            "attachment_processed": attachment_path,
        }
        
    except Exception as e:
        logger.error(f"Error in ask_with_attachment_and_actions: {str(e)}")
        return {
            "error": "agent_attachment_error",
            "message": str(e),
            "session_id": session_id or "",
            "actions_executed": [],
        }


@mcp.tool()
async def execute_command_tool(
    command: str,
    working_directory: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute a terminal command directly.
    
    This tool allows manual command execution without going through POE models.
    Useful for quick terminal operations or testing.
    
    Args:
        command: The command to execute
        working_directory: Directory to run the command in
        timeout: Timeout in seconds
        
    Returns:
        Command execution results
    """
    try:
        result = await execute_terminal_command(
            command=command,
            working_directory=working_directory or os.getcwd(),
            timeout=timeout
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return {
            "success": False,
            "action": "execute_command",
            "error": str(e)
        }


@mcp.tool()
async def create_file_tool(
    file_path: str,
    content: str,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Create a file with specified content.
    
    Args:
        file_path: Path where to create the file
        content: Content to write
        overwrite: Whether to overwrite existing files
        
    Returns:
        File creation results
    """
    try:
        result = await create_file_from_response(
            file_path=file_path,
            content=content,
            overwrite=overwrite
        )
        
        return result.dict()
        
    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        return {
            "success": False,
            "action": "create_file",
            "error": str(e)
        }


@mcp.tool()
def get_enhanced_server_info() -> Dict[str, Any]:
    """
    Get information about the enhanced POE MCP server.
    
    Returns:
        Enhanced server information including agent capabilities
    """
    try:
        # Get base server info
        base_info = get_server_info()
        
        # Add enhanced capabilities
        base_info.update({
            "agent_actions_enabled": True,
            "supported_actions": [
                "file_creation",
                "command_execution", 
                "editor_integration",
                "automatic_parsing"
            ],
            "warp_integration": True,
            "version_enhanced": "1.0.0"
        })
        
        return base_info
        
    except Exception as e:
        logger.error(f"Error getting enhanced server info: {str(e)}")
        return {
            "error": "server_info_error",
            "message": str(e)
        }


# Update startup handler to include our enhancements
@mcp.on_startup
async def enhanced_startup():
    """Enhanced startup handler."""
    logger.info("Starting Enhanced POE MCP Server with Warp Agent Integration")
    logger.info(f"Claude compatibility mode: {config.claude_compatible}")
    logger.info("Agent actions enabled: File creation, command execution, editor integration")
    
    # Start the session cleanup task (from original server)
    asyncio.create_task(cleanup_sessions_task())


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


def main():
    """Entry point for the enhanced server."""
    logger.info("Starting Enhanced POE Proxy MCP Server with STDIO transport")
    mcp.run()


if __name__ == "__main__":
    main()