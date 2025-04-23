#!/usr/bin/env python3
"""
File Utilities Module

This module provides utilities for file validation, reading, and temporary file creation.
"""
import os
import tempfile
import mimetypes
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

# Define maximum file size (10 MB by default)
DEFAULT_MAX_FILE_SIZE_MB = 10

# Define allowed file extensions
ALLOWED_TEXT_EXTENSIONS = [
    ".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".csv",
    ".yaml", ".yml", ".ini", ".cfg", ".conf", ".sh", ".bat", ".ps1", ".c",
    ".cpp", ".h", ".hpp", ".java", ".rb", ".php", ".go", ".rs", ".ts",
    ".jsx", ".tsx", ".vue", ".sql", ".log", ".tex", ".bib", ".rst",
]

ALLOWED_BINARY_EXTENSIONS = [
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods",
    ".odp", ".zip", ".tar", ".gz", ".7z", ".rar",
]

ALLOWED_EXTENSIONS = ALLOWED_TEXT_EXTENSIONS + ALLOWED_BINARY_EXTENSIONS


class FileHandlingError(Exception):
    """Exception raised for file handling errors."""
    pass


def validate_file(
    file_path: str,
    max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    allowed_extensions: Optional[List[str]] = None,
) -> bool:
    """
    Validate a file for size and extension.
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum file size in MB
        allowed_extensions: List of allowed file extensions
        
    Returns:
        True if the file is valid
        
    Raises:
        FileHandlingError: If the file is invalid
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileHandlingError(f"File not found: {file_path}")
    
    # Check if the file is a file (not a directory)
    if not os.path.isfile(file_path):
        raise FileHandlingError(f"Not a file: {file_path}")
    
    # Check file size
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        raise FileHandlingError(
            f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
        )
    
    # Check file extension
    if allowed_extensions is not None:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise FileHandlingError(
                f"File extension {file_extension} not allowed. "
                f"Allowed extensions: {', '.join(allowed_extensions)}"
            )
    
    return True


def is_text_file(file_path: str) -> bool:
    """
    Check if a file is a text file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file is a text file, False otherwise
    """
    # Check file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension in ALLOWED_TEXT_EXTENSIONS:
        return True
    
    # Try to detect by MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type and mime_type.startswith("text/"):
        return True
    
    # Try to read the file as text
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(1024)  # Read a small chunk
        return True
    except UnicodeDecodeError:
        return False


def read_file_content(file_path: str, max_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB) -> str:
    """
    Read the content of a text file.
    
    Args:
        file_path: Path to the file
        max_size_mb: Maximum file size in MB
        
    Returns:
        The content of the file
        
    Raises:
        FileHandlingError: If the file is invalid or cannot be read
    """
    # Validate the file
    validate_file(file_path, max_size_mb)
    
    # Check if it's a text file
    if not is_text_file(file_path):
        raise FileHandlingError(f"Not a text file: {file_path}")
    
    # Read the file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise FileHandlingError(f"Error reading file: {e}")


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """
    Create a temporary file with the given content.
    
    Args:
        content: The content to write to the file
        suffix: The file extension
        
    Returns:
        The path to the temporary file
        
    Raises:
        FileHandlingError: If the file cannot be created
    """
    try:
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        
        # Write the content to the file
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        
        return temp_path
    
    except Exception as e:
        raise FileHandlingError(f"Error creating temporary file: {e}")


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary with file information
        
    Raises:
        FileHandlingError: If the file is invalid
    """
    # Validate the file
    validate_file(file_path)
    
    # Get file information
    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    file_extension = os.path.splitext(file_path)[1].lower()
    mime_type, _ = mimetypes.guess_type(file_path)
    
    return {
        "path": file_path,
        "name": os.path.basename(file_path),
        "extension": file_extension,
        "size_bytes": file_size_bytes,
        "size_mb": file_size_mb,
        "mime_type": mime_type,
        "is_text": is_text_file(file_path),
    }