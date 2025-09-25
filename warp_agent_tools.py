#!/usr/bin/env python3
"""
Warp Agent Integration Tools for POE MCP

This module extends the POE MCP server with tools that can drive Warp terminal actions
based on responses from POE models.
"""
import os
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, Field

from utils import handle_exception, FileHandlingError


class WarpActionResult(BaseModel):
    """Result of a Warp agent action."""
    success: bool = Field(description="Whether the action succeeded")
    action: str = Field(description="The action that was performed")
    output: Optional[str] = Field(default=None, description="Output from the action")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class CommandExecution(BaseModel):
    """Configuration for command execution."""
    command: str = Field(description="Command to execute")
    working_directory: Optional[str] = Field(default=None, description="Working directory for command")
    timeout: Optional[int] = Field(default=30, description="Timeout in seconds")
    capture_output: bool = Field(default=True, description="Whether to capture output")


async def execute_terminal_command(
    command: str,
    working_directory: Optional[str] = None,
    timeout: int = 30,
    capture_output: bool = True
) -> WarpActionResult:
    """
    Execute a terminal command and return the result.
    
    Args:
        command: The command to execute
        working_directory: Directory to run the command in
        timeout: Timeout in seconds
        capture_output: Whether to capture and return output
        
    Returns:
        WarpActionResult with execution details
    """
    try:
        logger.debug(f"Executing command: {command}")
        
        # Security check - basic command validation
        dangerous_commands = ['rm -rf /', 'sudo rm', 'mkfs', 'dd if=', 'format']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return WarpActionResult(
                success=False,
                action="execute_command",
                error="Command rejected for security reasons"
            )
        
        # Set up process execution
        process_kwargs = {
            'shell': True,
            'timeout': timeout,
            'cwd': working_directory,
        }
        
        if capture_output:
            process_kwargs.update({
                'capture_output': True,
                'text': True
            })
        
        # Execute the command
        result = subprocess.run(command, **process_kwargs)
        
        output = None
        if capture_output:
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
        
        return WarpActionResult(
            success=result.returncode == 0,
            action="execute_command",
            output=output,
            error=None if result.returncode == 0 else f"Command failed with exit code {result.returncode}"
        )
        
    except subprocess.TimeoutExpired:
        return WarpActionResult(
            success=False,
            action="execute_command",
            error=f"Command timed out after {timeout} seconds"
        )
        
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return WarpActionResult(
            success=False,
            action="execute_command",
            error=str(e)
        )


async def create_file_from_response(
    file_path: str,
    content: str,
    overwrite: bool = False
) -> WarpActionResult:
    """
    Create a file with content provided by POE model response.
    
    Args:
        file_path: Path where to create the file
        content: Content to write to the file
        overwrite: Whether to overwrite existing files
        
    Returns:
        WarpActionResult with creation details
    """
    try:
        path = Path(file_path)
        
        # Check if file exists and overwrite is False
        if path.exists() and not overwrite:
            return WarpActionResult(
                success=False,
                action="create_file",
                error=f"File {file_path} already exists and overwrite=False"
            )
        
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the content
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created file: {file_path}")
        
        return WarpActionResult(
            success=True,
            action="create_file",
            output=f"Successfully created file: {file_path}"
        )
        
    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        return WarpActionResult(
            success=False,
            action="create_file",
            error=str(e)
        )


async def open_file_in_editor(
    file_path: str,
    editor: str = "code"  # Default to VS Code
) -> WarpActionResult:
    """
    Open a file in the specified editor.
    
    Args:
        file_path: Path to the file to open
        editor: Editor command (code, vim, nano, etc.)
        
    Returns:
        WarpActionResult with operation details
    """
    try:
        if not Path(file_path).exists():
            return WarpActionResult(
                success=False,
                action="open_file",
                error=f"File does not exist: {file_path}"
            )
        
        # Execute editor command
        command = f"{editor} {file_path}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        return WarpActionResult(
            success=result.returncode == 0,
            action="open_file",
            output=f"Opened {file_path} in {editor}",
            error=None if result.returncode == 0 else result.stderr
        )
        
    except Exception as e:
        logger.error(f"Error opening file: {str(e)}")
        return WarpActionResult(
            success=False,
            action="open_file",
            error=str(e)
        )


async def parse_and_execute_actions(
    poe_response: str,
    working_directory: Optional[str] = None
) -> List[WarpActionResult]:
    """
    Parse a POE model response for action directives and execute them.
    
    This function looks for common patterns in POE responses that indicate
    actions the user wants to take, such as:
    - File creation requests
    - Command execution requests
    - Editor opening requests
    
    Args:
        poe_response: The response text from a POE model
        working_directory: Working directory for any commands
        
    Returns:
        List of WarpActionResult objects for each action taken
    """
    results = []
    
    try:
        # Look for code blocks with file creation intent
        import re
        
        # Pattern for file creation: ```filename\ncode```
        file_pattern = r'```(\w+(?:\.\w+)?)\s*\n(.*?)\n```'
        file_matches = re.findall(file_pattern, poe_response, re.DOTALL)
        
        for filename, content in file_matches:
            # Check if the response indicates this should be saved
            context_before = poe_response[:poe_response.find(f'```{filename}')]
            if any(keyword in context_before.lower() for keyword in [
                'save', 'create', 'write', 'file', 'here\'s the', 'here is the'
            ]):
                result = await create_file_from_response(filename, content.strip())
                results.append(result)
        
        # Pattern for command execution: "run:" or "execute:"
        command_pattern = r'(?:run|execute):\s*`([^`]+)`'
        command_matches = re.findall(command_pattern, poe_response, re.IGNORECASE)
        
        for command in command_matches:
            result = await execute_terminal_command(
                command=command,
                working_directory=working_directory
            )
            results.append(result)
        
        # Pattern for opening files: "open file:" or similar
        open_pattern = r'open\s+(?:file\s+)?[`"\']([^`"\']+)[`"\']'
        open_matches = re.findall(open_pattern, poe_response, re.IGNORECASE)
        
        for file_path in open_matches:
            result = await open_file_in_editor(file_path)
            results.append(result)
            
    except Exception as e:
        logger.error(f"Error parsing actions from response: {str(e)}")
        results.append(WarpActionResult(
            success=False,
            action="parse_actions",
            error=str(e)
        ))
    
    return results


def format_action_results(results: List[WarpActionResult]) -> str:
    """
    Format action results for display to the user.
    
    Args:
        results: List of WarpActionResult objects
        
    Returns:
        Formatted string describing the actions taken
    """
    if not results:
        return "No actions were detected or executed."
    
    output = []
    success_count = sum(1 for r in results if r.success)
    
    output.append(f"Executed {len(results)} actions ({success_count} successful)")
    output.append("=" * 50)
    
    for i, result in enumerate(results, 1):
        status = "✓" if result.success else "✗"
        output.append(f"{i}. {status} {result.action}")
        
        if result.output:
            output.append(f"   Output: {result.output}")
        
        if result.error:
            output.append(f"   Error: {result.error}")
        
        if i < len(results):
            output.append("")
    
    return "\n".join(output)