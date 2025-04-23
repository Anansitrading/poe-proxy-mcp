#!/usr/bin/env python3
"""
Utilities Module

This module provides utilities for configuration and logging.
"""
import os
import sys
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class Config:
    """Configuration for the Poe Proxy MCP server."""
    
    poe_api_key: str
    debug_mode: bool = False
    claude_compatible: bool = True
    max_file_size_mb: int = 10
    session_expiry_minutes: int = 60


class PoeProxyError(Exception):
    """Base exception for Poe Proxy MCP server."""
    pass


class AuthenticationError(PoeProxyError):
    """Exception raised for authentication errors."""
    pass


class PoeApiError(PoeProxyError):
    """Exception raised for Poe API errors."""
    pass


class FileHandlingError(PoeProxyError):
    """Exception raised for file handling errors."""
    pass


def setup_logging(debug_mode: bool = False) -> logger:
    """
    Set up logging for the Poe Proxy MCP server.
    
    Args:
        debug_mode: Whether to enable debug mode
        
    Returns:
        Configured logger
    """
    # Remove default handlers
    logger.remove()
    
    # Add a handler for stderr
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    if debug_mode:
        # Debug mode: show all logs
        logger.add(sys.stderr, format=log_format, level="DEBUG")
        logger.add("poe_proxy_mcp_debug.log", format=log_format, level="DEBUG", rotation="10 MB", retention="1 week")
    else:
        # Normal mode: show info and above
        logger.add(sys.stderr, format=log_format, level="INFO")
        logger.add("poe_proxy_mcp.log", format=log_format, level="INFO", rotation="10 MB", retention="1 week")
    
    return logger


def get_config() -> Config:
    """
    Get the configuration for the Poe Proxy MCP server.
    
    Returns:
        Configuration object
    """
    # Get API key from environment variable
    poe_api_key = os.environ.get("POE_API_KEY", "")
    
    if not poe_api_key:
        logger.error("POE_API_KEY environment variable not set")
        raise AuthenticationError("POE_API_KEY environment variable not set")
    
    # Get other configuration from environment variables
    debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"
    claude_compatible = os.environ.get("CLAUDE_COMPATIBLE", "true").lower() == "true"
    
    try:
        max_file_size_mb = int(os.environ.get("MAX_FILE_SIZE_MB", "10"))
    except ValueError:
        max_file_size_mb = 10
        logger.warning("Invalid MAX_FILE_SIZE_MB value, using default: 10 MB")
    
    try:
        session_expiry_minutes = int(os.environ.get("SESSION_EXPIRY_MINUTES", "60"))
    except ValueError:
        session_expiry_minutes = 60
        logger.warning("Invalid SESSION_EXPIRY_MINUTES value, using default: 60 minutes")
    
    return Config(
        poe_api_key=poe_api_key,
        debug_mode=debug_mode,
        claude_compatible=claude_compatible,
        max_file_size_mb=max_file_size_mb,
        session_expiry_minutes=session_expiry_minutes,
    )


def handle_exception(exception: Exception) -> Dict[str, str]:
    """
    Handle exceptions and return a standardized error response.
    
    Args:
        exception: The exception to handle
        
    Returns:
        Dictionary with error information
    """
    error_type = type(exception).__name__
    error_message = str(exception)
    
    # Log the error
    logger.error(f"{error_type}: {error_message}")
    
    # Return a standardized error response
    if isinstance(exception, AuthenticationError):
        return {
            "error": "authentication_error",
            "message": error_message,
        }
    elif isinstance(exception, PoeApiError):
        return {
            "error": "poe_api_error",
            "message": error_message,
        }
    elif isinstance(exception, FileHandlingError):
        return {
            "error": "file_handling_error",
            "message": error_message,
        }
    else:
        return {
            "error": "internal_error",
            "message": f"{error_type}: {error_message}",
        }