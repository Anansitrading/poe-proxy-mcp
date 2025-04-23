"""
Logging utilities for the Poe Proxy MCP server.
"""
import os
import sys
from loguru import logger


def setup_logging(debug_mode=False):
    """
    Configure logging for the application.
    
    Args:
        debug_mode (bool): Whether to enable debug logging
    """
    # Remove default logger
    logger.remove()
    
    # Determine log level based on debug mode
    log_level = "DEBUG" if debug_mode else "INFO"
    
    # Add stdout handler with appropriate format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # Add file handler for error logs
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/poe_proxy_error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="1 week",
    )
    
    logger.info(f"Logging initialized with level: {log_level}")
    return logger


class PoeProxyError(Exception):
    """Base exception class for Poe Proxy MCP server errors."""
    pass


class AuthenticationError(PoeProxyError):
    """Raised when there's an issue with authentication."""
    pass


class PoeApiError(PoeProxyError):
    """Raised when there's an error from the Poe API."""
    pass


class FileHandlingError(PoeProxyError):
    """Raised when there's an issue handling files."""
    pass


def handle_exception(exc):
    """
    Handle exceptions and return appropriate error messages.
    
    Args:
        exc (Exception): The exception to handle
        
    Returns:
        dict: A dictionary with error details
    """
    error_type = type(exc).__name__
    error_msg = str(exc)
    
    if isinstance(exc, AuthenticationError):
        logger.error(f"Authentication error: {error_msg}")
        return {"error": "authentication_error", "message": error_msg}
    
    if isinstance(exc, PoeApiError):
        logger.error(f"Poe API error: {error_msg}")
        return {"error": "poe_api_error", "message": error_msg}
    
    if isinstance(exc, FileHandlingError):
        logger.error(f"File handling error: {error_msg}")
        return {"error": "file_handling_error", "message": error_msg}
    
    # Generic error handling
    logger.error(f"Unexpected error ({error_type}): {error_msg}")
    return {"error": "unexpected_error", "message": f"{error_type}: {error_msg}"}