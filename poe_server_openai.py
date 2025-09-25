#!/usr/bin/env python3
"""
POE Proxy MCP Server with OpenAI-Compatible Support

This server provides dual-client architecture:
1. Legacy fastapi_poe SDK for backward compatibility
2. New OpenAI-compatible client for advanced features

Features:
- Function calling/tools support
- Advanced parameters (temperature, max_tokens, top_p, stop)
- Multi-modal support (text, image, video, audio)
- Token usage tracking
- OpenAI-standard error handling
- Rate limiting with retry logic
"""
import os
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Import both clients for dual support
from poe_client import PoeClient, SessionManager
from poe_client.openai_client import (
    PoeOpenAIClient,
    OpenAICompletionRequest,
    TOOL_REGISTRY,
    EXAMPLE_TOOL_DEFINITIONS,
    example_get_weather,
    example_calculate,
)

from utils import (
    setup_logging,
    get_config,
    PoeProxyError,
    AuthenticationError,
    PoeApiError,
    FileHandlingError,
    handle_exception,
)

# Initialize logging and configuration
config = get_config()
logger = setup_logging(config.debug_mode)

# Create FastMCP server
mcp = FastMCP("POE Proxy MCP Server v2 - OpenAI Compatible")

# Initialize both clients
legacy_client = PoeClient(
    api_key=config.poe_api_key,
    debug_mode=config.debug_mode,
    claude_compatible=config.claude_compatible,
)

openai_client = PoeOpenAIClient(
    api_key=config.poe_api_key,
    base_url="https://api.poe.com/v1",
    async_mode=True,
    debug_mode=config.debug_mode,
)

session_manager = SessionManager(expiry_minutes=config.session_expiry_minutes)

# Register example tools
openai_client.register_tool("get_weather", example_get_weather, "Get weather information", 
                           EXAMPLE_TOOL_DEFINITIONS[0]["function"]["parameters"])
openai_client.register_tool("calculate", example_calculate, "Perform calculation",
                           EXAMPLE_TOOL_DEFINITIONS[1]["function"]["parameters"])


# Enhanced request models with OpenAI parameters
class EnhancedQueryRequest(BaseModel):
    """Enhanced query request with OpenAI-compatible parameters."""
    bot: str = Field(description="Model name (e.g., 'Claude-Opus-4.1', 'Gemini-2.5-Pro')")
    prompt: str = Field(description="The prompt to send")
    session_id: Optional[str] = Field(default=None, description="Session ID for context")
    use_openai_client: bool = Field(default=True, description="Use OpenAI-compatible client")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="Sampling temperature")
    top_p: Optional[float] = Field(default=None, ge=0, le=1, description="Nucleus sampling")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    stream: bool = Field(default=False, description="Enable streaming")


class FunctionCallRequest(BaseModel):
    """Request for function calling."""
    bot: str = Field(description="Model name")
    prompt: str = Field(description="The prompt")
    tools: List[Dict[str, Any]] = Field(description="Tool definitions in OpenAI format")
    tool_choice: Optional[Union[str, Dict]] = Field(default="auto", description="Tool selection")
    parallel_tool_calls: Optional[bool] = Field(default=True, description="Enable parallel execution")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)


@mcp.tool()
async def ask_poe_v2(
    bot: str,
    prompt: str,
    session_id: Optional[str] = None,
    use_openai_client: bool = True,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    stop: Optional[List[str]] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """
    Query POE with OpenAI-compatible parameters.
    
    This enhanced version supports both legacy and OpenAI clients,
    with advanced parameters like temperature, max_tokens, and stop sequences.
    
    Args:
        bot: Model name (e.g., 'Claude-Opus-4.1', 'Gemini-2.5-Pro', 'Grok-4')
        prompt: The prompt to send
        session_id: Optional session ID for context
        use_openai_client: Use OpenAI-compatible client (default: True)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0-2)
        top_p: Nucleus sampling parameter
        stop: Stop sequences
        stream: Enable streaming response
        
    Returns:
        Response with text, session_id, and usage statistics
    """
    try:
        current_session_id = session_manager.get_or_create_session(session_id)
        
        if use_openai_client:
            # Use OpenAI-compatible client
            messages = []
            
            # Get session messages if available
            if current_session_id:
                session_messages = session_manager.get_messages(current_session_id)
                for msg in session_messages:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Make OpenAI-compatible call
            response = await openai_client.chat_completion(
                model=bot,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop,
                stream=stream,
                user=current_session_id,
                auto_execute_tools=False,
            )
            
            if stream:
                # Return streaming generator
                return {
                    "stream": response,
                    "session_id": current_session_id,
                }
            
            # Extract response text
            response_text = response["choices"][0]["message"]["content"]
            
            # Update session
            session_manager.update_session(
                session_id=current_session_id,
                user_message=prompt,
                bot_message=response_text,
            )
            
            return {
                "text": response_text,
                "session_id": current_session_id,
                "model": response["model"],
                "usage": response.get("usage", {}),
                "finish_reason": response["choices"][0]["finish_reason"],
            }
        else:
            # Use legacy client for backward compatibility
            messages = session_manager.get_messages(current_session_id)
            
            async def stream_handler(text: str):
                if hasattr(mcp, "yield_progress"):
                    await mcp.yield_progress({"text": text})
            
            response = await legacy_client.query_model(
                bot_name=bot,
                prompt=prompt,
                messages=messages,
                stream_handler=stream_handler if not stream else None,
            )
            
            session_manager.update_session(
                session_id=current_session_id,
                user_message=prompt,
                bot_message=response["text"],
            )
            
            return {
                "text": response["text"],
                "session_id": current_session_id,
                "bot": bot,
            }
            
    except Exception as e:
        error_info = handle_exception(e)
        if use_openai_client:
            # Return OpenAI-compatible error format
            return openai_client.map_error_to_openai_format(e)
        else:
            return {
                "error": error_info["error"],
                "message": error_info["message"],
                "session_id": session_id or "",
            }


@mcp.tool()
async def ask_poe_with_tools(
    bot: str,
    prompt: str,
    tools: List[Dict[str, Any]],
    tool_choice: Optional[Union[str, Dict]] = "auto",
    parallel_tool_calls: Optional[bool] = True,
    session_id: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Query POE with function calling support.
    
    This tool enables function calling with POE models that support it,
    allowing for tool use, parallel execution, and automatic result handling.
    
    Args:
        bot: Model name (must support function calling)
        prompt: The prompt
        tools: List of tool definitions in OpenAI format
        tool_choice: How to select tools ("auto", "none", or specific tool)
        parallel_tool_calls: Enable parallel tool execution
        session_id: Optional session ID
        max_tokens: Maximum tokens
        temperature: Sampling temperature
        
    Returns:
        Response with tool calls executed and final answer
    """
    try:
        current_session_id = session_manager.get_or_create_session(session_id)
        
        # Get session messages
        messages = []
        if current_session_id:
            session_messages = session_manager.get_messages(current_session_id)
            for msg in session_messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        logger.info(f"Calling {bot} with {len(tools)} tools available")
        
        # Make OpenAI-compatible call with tools
        response = await openai_client.chat_completion(
            model=bot,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            max_tokens=max_tokens,
            temperature=temperature,
            user=current_session_id,
            auto_execute_tools=True,  # Automatically execute tool calls
        )
        
        # Extract response
        response_text = response["choices"][0]["message"]["content"]
        tool_calls = response["choices"][0]["message"].get("tool_calls", [])
        
        # Update session
        session_manager.update_session(
            session_id=current_session_id,
            user_message=prompt,
            bot_message=response_text,
        )
        
        return {
            "text": response_text,
            "session_id": current_session_id,
            "model": response["model"],
            "tool_calls": tool_calls,
            "usage": response.get("usage", {}),
            "finish_reason": response["choices"][0]["finish_reason"],
        }
        
    except Exception as e:
        logger.error(f"Function calling error: {str(e)}")
        return openai_client.map_error_to_openai_format(e)


@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = "GPT-Image-1",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate an image using POE image generation models.
    
    Args:
        prompt: Image generation prompt
        model: Image model (default: GPT-Image-1)
        session_id: Optional session ID
        
    Returns:
        Response with generated image or URL
    """
    try:
        current_session_id = session_manager.get_or_create_session(session_id)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Image generation should use stream=False as per documentation
        response = await openai_client.chat_completion(
            model=model,
            messages=messages,
            stream=False,
            user=current_session_id,
        )
        
        response_content = response["choices"][0]["message"]["content"]
        
        return {
            "content": response_content,
            "model": model,
            "session_id": current_session_id,
            "type": "image",
        }
        
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return openai_client.map_error_to_openai_format(e)


@mcp.tool()
async def generate_video(
    prompt: str,
    model: str = "Veo-3",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a video using POE video generation models.
    
    Args:
        prompt: Video generation prompt
        model: Video model (default: Veo-3)
        session_id: Optional session ID
        
    Returns:
        Response with generated video or URL
    """
    try:
        current_session_id = session_manager.get_or_create_session(session_id)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Video generation should use stream=False as per documentation
        response = await openai_client.chat_completion(
            model=model,
            messages=messages,
            stream=False,
            user=current_session_id,
        )
        
        response_content = response["choices"][0]["message"]["content"]
        
        return {
            "content": response_content,
            "model": model,
            "session_id": current_session_id,
            "type": "video",
        }
        
    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        return openai_client.map_error_to_openai_format(e)


@mcp.tool()
async def list_available_models_v2() -> Dict[str, Any]:
    """
    List available POE models with their capabilities.
    
    Returns updated model list including new models and their features.
    """
    models = {
        "text_models": [
            {"name": "Claude-Opus-4.1", "supports_tools": True, "max_tokens": 100000},
            {"name": "Claude-Sonnet-4", "supports_tools": True, "max_tokens": 100000},
            {"name": "Gemini-2.5-Pro", "supports_tools": True, "max_tokens": 100000},
            {"name": "GPT-4.1", "supports_tools": True, "max_tokens": 128000},
            {"name": "Grok-4", "supports_tools": True, "max_tokens": 100000},
            {"name": "Llama-3.1-405B", "supports_tools": False, "max_tokens": 100000},
        ],
        "image_models": [
            {"name": "GPT-Image-1", "type": "image_generation"},
        ],
        "video_models": [
            {"name": "Veo-3", "type": "video_generation"},
        ],
        "features": {
            "function_calling": True,
            "parallel_tools": True,
            "streaming": True,
            "temperature_control": True,
            "max_tokens_control": True,
            "stop_sequences": True,
            "usage_tracking": True,
        }
    }
    
    return models


@mcp.tool()
async def register_custom_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    implementation: str,
) -> Dict[str, Any]:
    """
    Register a custom tool for function calling.
    
    Args:
        name: Tool name
        description: Tool description
        parameters: JSON schema for parameters
        implementation: Python code as string (will be exec'd)
        
    Returns:
        Registration status
    """
    try:
        # Create function from implementation string
        exec_globals = {}
        exec(implementation, exec_globals)
        
        # Find the function in exec'd code
        func = None
        for item in exec_globals.values():
            if callable(item) and not item.__name__.startswith('_'):
                func = item
                break
        
        if not func:
            raise ValueError("No callable function found in implementation")
        
        # Register the tool
        openai_client.register_tool(name, func, description, parameters)
        
        return {
            "status": "success",
            "tool_name": name,
            "message": f"Tool '{name}' registered successfully",
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@mcp.tool()
async def get_server_info_v2() -> Dict[str, Any]:
    """
    Get server configuration and capabilities.
    
    Returns enhanced server information including OpenAI compatibility.
    """
    return {
        "version": "2.0.0",
        "features": {
            "legacy_client": True,
            "openai_client": True,
            "function_calling": True,
            "multi_modal": True,
            "streaming": True,
            "rate_limiting": True,
            "usage_tracking": True,
        },
        "configuration": {
            "debug_mode": config.debug_mode,
            "claude_compatible": config.claude_compatible,
            "max_file_size_mb": config.max_file_size_mb,
            "session_expiry_minutes": config.session_expiry_minutes,
        },
        "api_endpoints": {
            "poe_legacy": "fastapi_poe",
            "poe_openai": "https://api.poe.com/v1",
        },
        "registered_tools": list(TOOL_REGISTRY.keys()),
    }


# Main entry point
def main():
    """Run the MCP server in STDIO mode."""
    import sys
    from fastmcp.server import stdio_server
    
    logger.info("Starting POE Proxy MCP Server v2 with OpenAI compatibility")
    stdio_server(mcp)


if __name__ == "__main__":
    main()