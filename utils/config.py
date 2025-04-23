"""
Configuration utilities for the Poe Proxy MCP server.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .logging_utils import logger, AuthenticationError


# Load environment variables from .env file if it exists
load_dotenv()


class PoeProxyConfig(BaseModel):
    """Configuration for the Poe Proxy MCP server."""
    
    # Poe API configuration
    poe_api_key: str = Field(
        default_factory=lambda: os.getenv("POE_API_KEY", ""),
        description="Poe API key for authentication"
    )
    
    # Server configuration
    debug_mode: bool = Field(
        default_factory=lambda: os.getenv("DEBUG_MODE", "false").lower() == "true",
        description="Enable debug mode for verbose logging"
    )
    
    # Claude compatibility configuration
    claude_compatible: bool = Field(
        default_factory=lambda: os.getenv("USE_CLAUDE_COMPATIBLE", "false").lower() == "true",
        description="Enable Claude compatibility mode"
    )
    
    # File handling configuration
    max_file_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "10")),
        description="Maximum file size in MB for file uploads"
    )
    
    # Session management
    session_expiry_minutes: int = Field(
        default_factory=lambda: int(os.getenv("SESSION_EXPIRY_MINUTES", "60")),
        description="Session expiry time in minutes"
    )
    
    def validate_config(self) -> None:
        """
        Validate the configuration and raise exceptions for invalid values.
        
        Raises:
            AuthenticationError: If the Poe API key is missing
        """
        if not self.poe_api_key:
            raise AuthenticationError(
                "POE_API_KEY environment variable is required. "
                "Get your API key from https://poe.com/api_key"
            )
        
        logger.info(f"Configuration loaded successfully")
        if self.debug_mode:
            logger.debug(f"Debug mode enabled")
        if self.claude_compatible:
            logger.info(f"Claude compatibility mode enabled")
        
        return None


def get_config() -> PoeProxyConfig:
    """
    Get the configuration for the Poe Proxy MCP server.
    
    Returns:
        PoeProxyConfig: The configuration object
        
    Raises:
        AuthenticationError: If the configuration is invalid
    """
    config = PoeProxyConfig()
    config.validate_config()
    return config