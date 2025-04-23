"""
File handling utilities for the Poe API client.

This module provides functionality for handling file attachments,
including validation, processing, and MIME type detection.
"""
import os
import mimetypes
from typing import Dict, Optional, Tuple, BinaryIO
import tempfile

from utils import logger, FileHandlingError


def validate_file(file_path: str, max_size_mb: int = 10) -> Tuple[str, str]:
    """
    Validate a file for use with the Poe API.
    
    Args:
        file_path (str): Path to the file
        max_size_mb (int): Maximum file size in MB
        
    Returns:
        Tuple[str, str]: Tuple of (file_path, mime_type)
        
    Raises:
        FileHandlingError: If the file is invalid
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileHandlingError(f"File not found: {file_path}")
    
    # Check if file is a regular file
    if not os.path.isfile(file_path):
        raise FileHandlingError(f"Not a regular file: {file_path}")
    
    # Check file size
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise FileHandlingError(
            f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size "
            f"({max_size_mb} MB)"
        )
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Default to application/octet-stream if MIME type cannot be determined
        mime_type = "application/octet-stream"
    
    logger.debug(f"Validated file: {file_path} ({mime_type}, {file_size_mb:.2f} MB)")
    return file_path, mime_type


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is a text file.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if the file is a text file, False otherwise
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # Check if MIME type starts with text/
    if mime_type and mime_type.startswith("text/"):
        return True
    
    # Check common text file extensions
    text_extensions = [
        ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",
        ".css", ".js", ".py", ".java", ".c", ".cpp", ".h", ".hpp",
        ".sh", ".bat", ".ps1", ".yaml", ".yml", ".toml", ".ini",
        ".cfg", ".conf", ".log", ".sql", ".r", ".rb", ".pl", ".php",
    ]
    
    _, ext = os.path.splitext(file_path.lower())
    if ext in text_extensions:
        return True
    
    # Try to read the file as text
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(1024)  # Read a small chunk
        return True
    except UnicodeDecodeError:
        return False


def read_file_content(file_path: str, max_size_mb: int = 10) -> Tuple[str, bool]:
    """
    Read the content of a file.
    
    Args:
        file_path (str): Path to the file
        max_size_mb (int): Maximum file size in MB
        
    Returns:
        Tuple[str, bool]: Tuple of (content, is_text)
        
    Raises:
        FileHandlingError: If there's an error reading the file
    """
    try:
        # Validate the file
        validate_file(file_path, max_size_mb)
        
        # Check if it's a text file
        is_text = is_text_file(file_path)
        
        if is_text:
            # Read as text
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content, True
        else:
            # For binary files, return the file name
            return os.path.basename(file_path), False
    
    except Exception as e:
        raise FileHandlingError(f"Error reading file: {str(e)}")


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """
    Create a temporary file with the given content.
    
    Args:
        content (str): Content to write to the file
        suffix (str): File suffix/extension
        
    Returns:
        str: Path to the temporary file
        
    Raises:
        FileHandlingError: If there's an error creating the file
    """
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.debug(f"Created temporary file: {temp_file_path}")
        return temp_file_path
    
    except Exception as e:
        raise FileHandlingError(f"Error creating temporary file: {str(e)}")


def get_common_mime_types() -> Dict[str, str]:
    """
    Get a dictionary of common file extensions and their MIME types.
    
    Returns:
        Dict[str, str]: Dictionary of file extensions to MIME types
    """
    return {
        # Text
        ".txt": "text/plain",
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".csv": "text/csv",
        
        # Application
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".zip": "application/zip",
        ".xml": "application/xml",
        
        # Image
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        
        # Audio
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        
        # Video
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
        ".webm": "video/webm",
        
        # Code
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".java": "text/x-java",
        ".c": "text/x-c",
        ".cpp": "text/x-c++",
        ".rb": "text/x-ruby",
        ".go": "text/x-go",
        ".rs": "text/x-rust",
        ".php": "text/x-php",
    }