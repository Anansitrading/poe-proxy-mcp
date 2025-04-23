"""
Claude 3.7 Sonnet compatibility module for the Poe API client.

This module provides functionality for ensuring compatibility with Claude 3.7 Sonnet,
particularly for handling the thinking protocol.
"""
from typing import Dict, Any, Optional, List
import json

from utils import logger


def format_thinking_protocol(thinking: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Format the thinking protocol for Claude 3.7 Sonnet.
    
    Args:
        thinking (Optional[Dict[str, Any]]): The thinking protocol parameters
        
    Returns:
        Optional[Dict[str, Any]]: The formatted thinking protocol
    """
    if not thinking:
        return None
    
    # Ensure the thinking protocol has the required fields
    formatted_thinking = {
        "thinking": True,
    }
    
    # Copy any additional fields from the input thinking
    if isinstance(thinking, dict):
        for key, value in thinking.items():
            formatted_thinking[key] = value
    
    logger.debug(f"Formatted thinking protocol: {formatted_thinking}")
    return formatted_thinking


def process_claude_response(response: str) -> str:
    """
    Process a response from Claude 3.7 Sonnet to handle thinking protocol output.
    
    Args:
        response (str): The response from Claude
        
    Returns:
        str: The processed response
    """
    # Check if the response contains thinking protocol output
    if "<thinking>" in response and "</thinking>" in response:
        # Extract the thinking protocol output
        thinking_start = response.find("<thinking>")
        thinking_end = response.find("</thinking>") + len("</thinking>")
        thinking_text = response[thinking_start:thinking_end]
        
        # Remove the thinking protocol output from the response
        response = response[:thinking_start] + response[thinking_end:]
        
        logger.debug(f"Removed thinking protocol output: {thinking_text}")
    
    return response


def handle_claude_error(error: Exception) -> Dict[str, str]:
    """
    Handle errors specific to Claude 3.7 Sonnet.
    
    Args:
        error (Exception): The error to handle
        
    Returns:
        Dict[str, str]: Error information
    """
    error_msg = str(error)
    
    # Check for common Claude 3.7 Sonnet errors
    if "thinking protocol" in error_msg.lower():
        logger.warning(f"Claude thinking protocol error: {error_msg}")
        return {
            "error": "claude_thinking_protocol_error",
            "message": "Error with Claude thinking protocol. Try again without the thinking parameter.",
        }
    
    if "context window" in error_msg.lower() or "token limit" in error_msg.lower():
        logger.warning(f"Claude context window error: {error_msg}")
        return {
            "error": "claude_context_window_error",
            "message": "The input exceeds Claude's context window. Try reducing the input size or using a model with a larger context window.",
        }
    
    # Generic Claude error
    logger.error(f"Claude error: {error_msg}")
    return {
        "error": "claude_error",
        "message": f"Error with Claude: {error_msg}",
    }


def is_claude_model(model_name: str) -> bool:
    """
    Check if a model is a Claude model.
    
    Args:
        model_name (str): The name of the model
        
    Returns:
        bool: True if the model is a Claude model, False otherwise
    """
    claude_models = [
        "Claude-3-Opus-200k",
        "Claude-3-Sonnet-7k",
        "Claude-3-Haiku-3k",
        "Claude-2-100k",
    ]
    
    # Check if the model name is in the list of Claude models
    for claude_model in claude_models:
        if claude_model.lower() in model_name.lower() or model_name.lower() in claude_model.lower():
            return True
    
    return False