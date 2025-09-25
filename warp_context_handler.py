"""
Warp terminal integration for POE MCP server.

This module handles:
- Context extraction from Warp (terminal output, files, git state)
- Output formatting for Warp rendering
- Command execution and file operations
- Media display in Warp
"""
import os
import json
import base64
import subprocess
import asyncio
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class BlockType(Enum):
    """Warp block types for output formatting."""
    TEXT = "text"
    CODE = "code"
    COMMAND = "command"
    FILE = "file"
    MEDIA = "media"
    TABLE = "table"
    PARAGRAPH = "paragraph"
    STRUCTURED = "structured"
    OUTPUT = "output"
    ERROR = "error"


@dataclass
class WarpBlock:
    """Represents a Warp output block."""
    type: BlockType
    text: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    url: Optional[str] = None
    media_type: Optional[str] = None
    filename: Optional[str] = None
    filepath: Optional[str] = None
    content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"type": self.type.value}
        for key, value in asdict(self).items():
            if key != "type" and value is not None:
                result[key] = value
        return result


class WarpContextExtractor:
    """Extract context from Warp terminal."""
    
    @staticmethod
    def extract_from_request(request_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract context from Warp MCP request.
        
        Args:
            request_context: Context object from Warp MCP request
            
        Returns:
            Processed context dictionary
        """
        context = {
            'blocks': [],
            'selection': None,
            'cwd': None,
            'git': {},
            'env': {},
            'references': [],
            'attachments': [],
        }
        
        # Extract terminal blocks
        if 'blocks' in request_context:
            for block in request_context['blocks']:
                context['blocks'].append({
                    'text': block.get('text', ''),
                    'type': block.get('type', 'output'),
                    'meta': block.get('meta', {}),
                })
        
        # Extract selection
        if 'selection' in request_context:
            context['selection'] = request_context['selection']
        
        # Extract working directory
        context['cwd'] = request_context.get('cwd', os.getcwd())
        
        # Extract git state
        if 'git' in request_context:
            context['git'] = request_context['git']
        else:
            # Try to get git state if not provided
            context['git'] = WarpContextExtractor._get_git_state(context['cwd'])
        
        # Extract environment
        context['env'] = request_context.get('env', dict(os.environ))
        
        # Extract file references (@mentions)
        if 'references' in request_context:
            context['references'] = request_context['references']
        
        # Extract attachments
        if 'attachments' in request_context:
            context['attachments'] = request_context['attachments']
        
        return context
    
    @staticmethod
    def _get_git_state(cwd: str) -> Dict[str, Any]:
        """Get current git state."""
        git_info = {}
        try:
            # Get branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                git_info['branch'] = result.stdout.strip()
            
            # Get status
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                git_info['status'] = result.stdout
                git_info['dirty'] = bool(result.stdout.strip())
            
            # Get remote
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=cwd,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                git_info['remote'] = result.stdout.strip()
                
        except Exception as e:
            logger.debug(f"Could not get git state: {e}")
        
        return git_info
    
    @staticmethod
    def extract_terminal_output(blocks: List[Dict]) -> str:
        """Extract terminal output from blocks."""
        output_lines = []
        for block in blocks:
            if block.get('type') == 'output':
                output_lines.append(block.get('text', ''))
        return '\n'.join(output_lines)
    
    @staticmethod
    def extract_selected_text(context: Dict[str, Any]) -> Optional[str]:
        """Extract selected text from context."""
        if not context.get('selection'):
            return None
        
        selection = context['selection']
        blocks = context.get('blocks', [])
        
        # Extract based on selection indices
        if 'block_index' in selection and 'start' in selection and 'end' in selection:
            block_idx = selection['block_index']
            if 0 <= block_idx < len(blocks):
                text = blocks[block_idx].get('text', '')
                start = selection.get('start', 0)
                end = selection.get('end', len(text))
                return text[start:end]
        
        return None
    
    @staticmethod
    def extract_file_references(context: Dict[str, Any]) -> List[str]:
        """Extract file paths from @mentions."""
        files = []
        for ref in context.get('references', []):
            if ref.get('type') == 'file':
                files.append(ref.get('path'))
        return files


class WarpOutputFormatter:
    """Format output for Warp terminal display."""
    
    @staticmethod
    def create_code_block(
        code: str,
        language: str = "python",
        line_numbers: bool = False
    ) -> WarpBlock:
        """Create a code block with syntax highlighting."""
        return WarpBlock(
            type=BlockType.CODE,
            text=code,
            meta={"language": language, "line_numbers": line_numbers}
        )
    
    @staticmethod
    def create_command_block(
        command: str,
        executable: bool = True,
        description: Optional[str] = None
    ) -> WarpBlock:
        """Create a clickable command block."""
        actions = []
        if executable:
            actions.append({"type": "run", "command": command})
        
        block = WarpBlock(
            type=BlockType.COMMAND,
            text=command,
            actions=actions
        )
        
        if description:
            block.meta = {"description": description}
        
        return block
    
    @staticmethod
    def create_file_block(
        filename: str,
        content: str,
        filepath: Optional[str] = None
    ) -> WarpBlock:
        """Create a file block for saving/downloading."""
        return WarpBlock(
            type=BlockType.FILE,
            filename=filename,
            filepath=filepath or f"/tmp/{filename}",
            content=content
        )
    
    @staticmethod
    def create_media_block(
        url: Optional[str] = None,
        path: Optional[str] = None,
        media_type: str = "image/png"
    ) -> WarpBlock:
        """Create an inline media block."""
        if path and not url:
            # Convert local file to data URL
            url = WarpOutputFormatter._file_to_data_url(path, media_type)
        
        return WarpBlock(
            type=BlockType.MEDIA,
            url=url,
            media_type=media_type
        )
    
    @staticmethod
    def create_text_block(text: str) -> WarpBlock:
        """Create a simple text block."""
        return WarpBlock(
            type=BlockType.TEXT,
            text=text
        )
    
    @staticmethod
    def create_error_block(error: str, details: Optional[str] = None) -> WarpBlock:
        """Create an error block."""
        text = f"❌ Error: {error}"
        if details:
            text += f"\n\nDetails:\n{details}"
        
        return WarpBlock(
            type=BlockType.ERROR,
            text=text,
            meta={"severity": "error"}
        )
    
    @staticmethod
    def _file_to_data_url(filepath: str, media_type: str) -> str:
        """Convert file to data URL for inline display."""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
                b64 = base64.b64encode(data).decode('utf-8')
                return f"data:{media_type};base64,{b64}"
        except Exception as e:
            logger.error(f"Failed to convert file to data URL: {e}")
            return ""
    
    @staticmethod
    def format_response(
        text: Optional[str] = None,
        code: Optional[Dict[str, str]] = None,
        commands: Optional[List[str]] = None,
        files: Optional[Dict[str, str]] = None,
        images: Optional[List[str]] = None,
        videos: Optional[List[str]] = None,
        errors: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Format a complete response for Warp.
        
        Args:
            text: Plain text content
            code: Code snippets {filename: content}
            commands: Shell commands to display
            files: Files to create {filename: content}
            images: Image paths to display inline
            videos: Video paths to display
            errors: Error messages
            
        Returns:
            List of Warp blocks as dictionaries
        """
        blocks = []
        
        # Add text blocks
        if text:
            blocks.append(WarpOutputFormatter.create_text_block(text).to_dict())
        
        # Add code blocks
        if code:
            for filename, content in code.items():
                lang = Path(filename).suffix.lstrip('.') or 'text'
                blocks.append(
                    WarpOutputFormatter.create_code_block(content, lang).to_dict()
                )
        
        # Add command blocks
        if commands:
            for cmd in commands:
                blocks.append(
                    WarpOutputFormatter.create_command_block(cmd).to_dict()
                )
        
        # Add file blocks
        if files:
            for filename, content in files.items():
                blocks.append(
                    WarpOutputFormatter.create_file_block(filename, content).to_dict()
                )
        
        # Add image blocks
        if images:
            for img_path in images:
                blocks.append(
                    WarpOutputFormatter.create_media_block(
                        path=img_path,
                        media_type="image/png"
                    ).to_dict()
                )
        
        # Add video blocks
        if videos:
            for vid_path in videos:
                blocks.append(
                    WarpOutputFormatter.create_media_block(
                        path=vid_path,
                        media_type="video/mp4"
                    ).to_dict()
                )
        
        # Add error blocks
        if errors:
            for error in errors:
                blocks.append(
                    WarpOutputFormatter.create_error_block(error).to_dict()
                )
        
        return blocks


class WarpActionExecutor:
    """Execute actions from POE responses in Warp terminal."""
    
    @staticmethod
    async def execute_command(
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a shell command."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                'success': process.returncode == 0,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'returncode': process.returncode,
                'command': command
            }
            
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f"Command timed out after {timeout}s",
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command
            }
    
    @staticmethod
    async def create_file(
        filepath: str,
        content: str,
        mode: str = 'w'
    ) -> Dict[str, Any]:
        """Create or modify a file."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'filepath': str(path.absolute()),
                'size': len(content)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filepath': filepath
            }
    
    @staticmethod
    async def parse_and_execute_actions(
        poe_response: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse POE response for actions and execute them.
        
        Actions are detected by special markers:
        - [EXECUTE]: command
        - [CREATE_FILE]: filepath
        - [EDIT_FILE]: filepath
        """
        results = []
        lines = poe_response.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Detect command execution
            if line.startswith('[EXECUTE]:'):
                command = line[10:].strip()
                result = await WarpActionExecutor.execute_command(
                    command,
                    cwd=context.get('cwd')
                )
                results.append(result)
            
            # Detect file creation
            elif line.startswith('[CREATE_FILE]:'):
                filepath = line[14:].strip()
                # Collect content until next marker or end
                content_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith('['):
                    content_lines.append(lines[i])
                    i += 1
                i -= 1  # Back up one line
                
                content = '\n'.join(content_lines)
                result = await WarpActionExecutor.create_file(filepath, content)
                results.append(result)
            
            i += 1
        
        return results


class WarpMCPIntegration:
    """Main integration class for Warp MCP protocol."""
    
    def __init__(self):
        self.context_extractor = WarpContextExtractor()
        self.output_formatter = WarpOutputFormatter()
        self.action_executor = WarpActionExecutor()
    
    async def handle_request(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a complete Warp MCP request.
        
        Args:
            request: Warp MCP request payload
            
        Returns:
            Formatted response with blocks
        """
        # Extract context
        context = self.context_extractor.extract_from_request(
            request.get('context', {})
        )
        
        # Log context info
        logger.info(f"Processing request in {context.get('cwd')}")
        if context.get('git', {}).get('branch'):
            logger.info(f"Git branch: {context['git']['branch']}")
        
        # Process the request (placeholder for actual logic)
        response_blocks = []
        
        # Add context summary
        response_blocks.append(
            self.output_formatter.create_text_block(
                f"📂 Working in: {context.get('cwd')}"
            ).to_dict()
        )
        
        if context.get('selection'):
            selected = self.context_extractor.extract_selected_text(context)
            if selected:
                response_blocks.append(
                    self.output_formatter.create_text_block(
                        f"📝 Selected: {selected[:100]}..."
                    ).to_dict()
                )
        
        return {"blocks": response_blocks}
    
    def format_poe_response(
        self,
        poe_response: str,
        response_type: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        Format POE response for Warp display.
        
        Args:
            poe_response: Raw POE response text
            response_type: Type of response (text, code, mixed)
            
        Returns:
            List of formatted Warp blocks
        """
        blocks = []
        
        # Parse response for different content types
        # This is a simplified parser - enhance based on actual POE output
        lines = poe_response.split('\n')
        current_code = []
        current_text = []
        in_code_block = False
        
        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End code block
                    if current_code:
                        code = '\n'.join(current_code)
                        blocks.append(
                            self.output_formatter.create_code_block(code).to_dict()
                        )
                        current_code = []
                    in_code_block = False
                else:
                    # Start code block
                    if current_text:
                        text = '\n'.join(current_text)
                        blocks.append(
                            self.output_formatter.create_text_block(text).to_dict()
                        )
                        current_text = []
                    in_code_block = True
            elif in_code_block:
                current_code.append(line)
            else:
                current_text.append(line)
        
        # Add remaining content
        if current_text:
            text = '\n'.join(current_text)
            blocks.append(
                self.output_formatter.create_text_block(text).to_dict()
            )
        
        if current_code:
            code = '\n'.join(current_code)
            blocks.append(
                self.output_formatter.create_code_block(code).to_dict()
            )
        
        return blocks


# Global integration instance
warp_integration = WarpMCPIntegration()