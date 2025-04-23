#!/usr/bin/env python3
"""
Claude Compatibility Module (SDK-Compatible Version)

This module provides enhanced compatibility with Claude 3.7 Sonnet's thinking protocol,
following the approach used in the official Python MCP SDK.
"""
import json
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List, Union

from loguru import logger

# Define Claude-specific constants
CLAUDE_MODELS = [
    "claude",
    "claude-3",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
]

# Default thinking protocol parameters
DEFAULT_THINKING = {
    "enabled": True,
    "template": "{{thinking}}",
    "include_in_response": False,
}


def is_claude_model(model_name: str) -> bool:
    """
    Check if a model is a Claude model.
    
    Args:
        model_name: The name of the model to check
        
    Returns:
        True if the model is a Claude model, False otherwise
    """
    model_name = model_name.lower()
    return any(claude_model in model_name for claude_model in CLAUDE_MODELS)


def format_thinking_protocol(
    prompt: str,
    thinking: Optional[Dict[str, Any]] = None,
    model_name: str = "",
) -> str:
    """
    Format a prompt with Claude's thinking protocol.
    
    This function follows the approach used in the official Python MCP SDK,
    which allows for customization of the thinking protocol parameters.
    
    Args:
        prompt: The original prompt to format
        thinking: Optional parameters for the thinking protocol
        model_name: The name of the model (to check if it's Claude)
        
    Returns:
        The formatted prompt with thinking protocol
    """
    # If thinking is None or disabled, or if the model is not Claude, return the original prompt
    if thinking is None or thinking.get("enabled", True) is False or not is_claude_model(model_name):
        return prompt
    
    # Get thinking parameters with defaults
    template = thinking.get("template", DEFAULT_THINKING["template"])
    
    # Check if the template is valid
    if "{{thinking}}" not in template:
        logger.warning("Invalid thinking template, must contain {{thinking}}. Using default.")
        template = DEFAULT_THINKING["template"]
    
    # Format the prompt with the thinking protocol
    formatted_prompt = f"{prompt}\n\n{template}"
    
    return formatted_prompt


def extract_thinking_from_response(
    response: str,
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Extract thinking from a Claude response.
    
    Args:
        response: The response from Claude
        thinking: Optional parameters for the thinking protocol
        
    Returns:
        Dictionary with the extracted thinking and the cleaned response
    """
    if thinking is None or thinking.get("enabled", True) is False:
        return {"thinking": "", "response": response}
    
    # Get thinking parameters with defaults
    template = thinking.get("template", DEFAULT_THINKING["template"])
    include_in_response = thinking.get("include_in_response", DEFAULT_THINKING["include_in_response"])
    
    # Replace {{thinking}} with a regex pattern to extract thinking
    pattern_str = template.replace("{{thinking}}", "(.*?)")
    
    # Try to extract thinking using the pattern
    import re
    pattern = re.compile(pattern_str, re.DOTALL)
    match = pattern.search(response)
    
    if match:
        thinking_text = match.group(1).strip()
        
        # Remove the thinking from the response if not included
        if not include_in_response:
            cleaned_response = pattern.sub("", response).strip()
        else:
            cleaned_response = response
        
        return {"thinking": thinking_text, "response": cleaned_response}
    
    # If no thinking found, return the original response
    return {"thinking": "", "response": response}


def process_claude_response(
    response: str,
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Process a Claude response to handle the thinking protocol.
    
    Args:
        response: The response from Claude
        thinking: Optional parameters for the thinking protocol
        
    Returns:
        Dictionary with the processed response and any extracted thinking
    """
    if thinking is None or thinking.get("enabled", True) is False:
        return {"text": response, "thinking": ""}
    
    # Extract thinking from the response
    extracted = extract_thinking_from_response(response, thinking)
    
    return {
        "text": extracted["response"],
        "thinking": extracted["thinking"],
    }


async def handle_claude_error(
    error: Exception,
    fallback_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, str]]]] = None,
    prompt: str = "",
    model_name: str = "",
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handle Claude-specific errors, especially those related to the thinking protocol.
    
    This function implements a fallback mechanism for thinking protocol issues,
    attempting to retry the query without the thinking protocol if it fails.
    
    Args:
        error: The exception that occurred
        fallback_handler: Optional function to handle fallback queries
        prompt: The original prompt
        model_name: The name of the model
        thinking: The thinking protocol parameters
        
    Returns:
        Dictionary with error information and any fallback response
    """
    error_str = str(error).lower()
    
    # Check if the error is related to the thinking protocol
    thinking_related_errors = [
        "thinking",
        "protocol",
        "template",
        "format",
        "invalid request",
        "bad request",
    ]
    
    is_thinking_error = any(err in error_str for err in thinking_related_errors)
    
    # If it's a thinking protocol error and we have a fallback handler
    if is_thinking_error and fallback_handler and is_claude_model(model_name):
        logger.warning(f"Claude thinking protocol error: {error_str}. Attempting fallback without thinking protocol.")
        
        try:
            # Try again without the thinking protocol
            disabled_thinking = {"enabled": False}
            
            # Call the fallback handler
            fallback_response = await fallback_handler(prompt, disabled_thinking)
            
            return {
                "text": fallback_response.get("text", ""),
                "error": True,
                "error_message": f"Thinking protocol error: {error_str}. Fallback response provided.",
                "fallback_used": True,
            }
        
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            
            return {
                "text": "",
                "error": True,
                "error_message": f"Thinking protocol error: {error_str}. Fallback also failed: {str(fallback_error)}",
                "fallback_used": True,
                "fallback_failed": True,
            }
    
    # For non-thinking errors or if no fallback handler
    return {
        "text": "",
        "error": True,
        "error_message": f"Error: {str(error)}",
        "fallback_used": False,
    }


class ClaudeThinkingProtocol:
    """
    A class to handle Claude's thinking protocol in a more structured way.
    
    This class provides methods for formatting prompts with the thinking protocol,
    processing responses, and handling errors.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        template: str = "{{thinking}}",
        include_in_response: bool = False,
    ):
        """
        Initialize the Claude thinking protocol handler.
        
        Args:
            enabled: Whether the thinking protocol is enabled
            template: The template to use for the thinking protocol
            include_in_response: Whether to include thinking in the response
        """
        self.enabled = enabled
        self.template = template
        self.include_in_response = include_in_response
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current thinking protocol configuration.
        
        Returns:
            Dictionary with the current configuration
        """
        return {
            "enabled": self.enabled,
            "template": self.template,
            "include_in_response": self.include_in_response,
        }
    
    def format_prompt(self, prompt: str, model_name: str = "") -> str:
        """
        Format a prompt with the thinking protocol.
        
        Args:
            prompt: The original prompt to format
            model_name: The name of the model
            
        Returns:
            The formatted prompt
        """
        return format_thinking_protocol(
            prompt=prompt,
            thinking=self.get_config(),
            model_name=model_name,
        )
    
    def process_response(self, response: str) -> Dict[str, str]:
        """
        Process a response with the thinking protocol.
        
        Args:
            response: The response to process
            
        Returns:
            Dictionary with the processed response and any extracted thinking
        """
        return process_claude_response(
            response=response,
            thinking=self.get_config(),
        )
    
    async def handle_error(
        self,
        error: Exception,
        fallback_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[Dict[str, str]]]] = None,
        prompt: str = "",
        model_name: str = "",
    ) -> Dict[str, Any]:
        """
        Handle errors related to the thinking protocol.
        
        Args:
            error: The exception that occurred
            fallback_handler: Optional function to handle fallback queries
            prompt: The original prompt
            model_name: The name of the model
            
        Returns:
            Dictionary with error information and any fallback response
        """
        return await handle_claude_error(
            error=error,
            fallback_handler=fallback_handler,
            prompt=prompt,
            model_name=model_name,
            thinking=self.get_config(),
        )