"""
Enhanced streaming support for POE MCP server.

This module implements:
- SSE (Server-Sent Events) formatting
- Delta content streaming for tool calls
- Chunk aggregation and buffering
- Error recovery in streams
"""
import json
import asyncio
import time
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class StreamEventType(Enum):
    """SSE event types."""
    MESSAGE = "message"
    DELTA = "delta"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    PING = "ping"
    COMPLETE = "complete"


@dataclass
class StreamEvent:
    """Represents a streaming event."""
    event: StreamEventType
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None
    
    def to_sse(self) -> str:
        """Convert to SSE format."""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.event != StreamEventType.MESSAGE:
            lines.append(f"event: {self.event.value}")
        
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        
        # Format data as JSON
        if isinstance(self.data, str):
            data_str = self.data
        else:
            data_str = json.dumps(self.data)
        
        lines.append(f"data: {data_str}")
        
        return "\n".join(lines) + "\n\n"


class ChunkAggregator:
    """Aggregates streaming chunks into complete responses."""
    
    def __init__(self, max_buffer_size: int = 10000):
        """
        Initialize chunk aggregator.
        
        Args:
            max_buffer_size: Maximum characters to buffer
        """
        self.buffer: List[str] = []
        self.max_buffer_size = max_buffer_size
        self.total_size = 0
        self.tool_calls = []
        self.metadata = {}
    
    def add_chunk(self, chunk: Dict[str, Any]) -> None:
        """Add a chunk to the buffer."""
        # Extract content
        if 'choices' in chunk:
            for choice in chunk['choices']:
                delta = choice.get('delta', {})
                
                # Handle text content
                if 'content' in delta and delta['content']:
                    content = delta['content']
                    self.buffer.append(content)
                    self.total_size += len(content)
                
                # Handle tool calls
                if 'tool_calls' in delta and delta['tool_calls']:
                    self.tool_calls.extend(delta['tool_calls'])
        
        # Store metadata
        if 'id' in chunk:
            self.metadata['id'] = chunk['id']
        if 'model' in chunk:
            self.metadata['model'] = chunk['model']
    
    def get_aggregated(self) -> str:
        """Get aggregated content."""
        return ''.join(self.buffer)
    
    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Get aggregated tool calls."""
        return self.tool_calls
    
    def clear(self) -> None:
        """Clear the buffer."""
        self.buffer.clear()
        self.tool_calls.clear()
        self.total_size = 0
        self.metadata.clear()
    
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self.total_size >= self.max_buffer_size


class SSEStreamer:
    """
    Server-Sent Events streamer with error recovery.
    """
    
    def __init__(
        self,
        retry_ms: int = 3000,
        ping_interval: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize SSE streamer.
        
        Args:
            retry_ms: Client retry interval in milliseconds
            ping_interval: Ping interval in seconds
            max_retries: Maximum retry attempts for errors
        """
        self.retry_ms = retry_ms
        self.ping_interval = ping_interval
        self.max_retries = max_retries
        self.aggregator = ChunkAggregator()
        self.event_id = 0
        self.error_count = 0
    
    async def stream_response(
        self,
        response_generator: AsyncGenerator[Dict[str, Any], None],
        include_aggregation: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Stream response as SSE.
        
        Args:
            response_generator: Async generator of response chunks
            include_aggregation: Whether to send aggregated content at end
            
        Yields:
            SSE-formatted strings
        """
        # Send initial retry interval
        yield StreamEvent(
            event=StreamEventType.MESSAGE,
            data={"type": "init", "retry": self.retry_ms},
            retry=self.retry_ms
        ).to_sse()
        
        # Start ping task
        ping_task = asyncio.create_task(self._ping_generator())
        
        try:
            async for chunk in response_generator:
                try:
                    # Process chunk
                    self.aggregator.add_chunk(chunk)
                    
                    # Create delta event
                    event = StreamEvent(
                        event=StreamEventType.DELTA,
                        data=chunk,
                        id=str(self.event_id)
                    )
                    self.event_id += 1
                    
                    yield event.to_sse()
                    
                    # Reset error count on successful chunk
                    self.error_count = 0
                    
                except Exception as e:
                    # Handle error with recovery
                    self.error_count += 1
                    
                    if self.error_count <= self.max_retries:
                        logger.warning(f"Stream error (attempt {self.error_count}): {e}")
                        
                        # Send error event
                        error_event = StreamEvent(
                            event=StreamEventType.ERROR,
                            data={
                                "error": str(e),
                                "recoverable": True,
                                "attempt": self.error_count
                            }
                        )
                        yield error_event.to_sse()
                        
                        # Wait before retry
                        await asyncio.sleep(1 * self.error_count)
                    else:
                        # Fatal error
                        logger.error(f"Stream fatal error after {self.max_retries} attempts: {e}")
                        
                        error_event = StreamEvent(
                            event=StreamEventType.ERROR,
                            data={
                                "error": str(e),
                                "recoverable": False
                            }
                        )
                        yield error_event.to_sse()
                        break
            
            # Send completion event with aggregation
            if include_aggregation:
                complete_event = StreamEvent(
                    event=StreamEventType.COMPLETE,
                    data={
                        "content": self.aggregator.get_aggregated(),
                        "tool_calls": self.aggregator.get_tool_calls(),
                        "metadata": self.aggregator.metadata
                    },
                    id=str(self.event_id)
                )
                yield complete_event.to_sse()
            
        finally:
            # Cancel ping task
            ping_task.cancel()
            try:
                await ping_task
            except asyncio.CancelledError:
                pass
    
    async def _ping_generator(self) -> None:
        """Generate periodic ping events."""
        while True:
            await asyncio.sleep(self.ping_interval)
            # Ping events are handled by the main stream
            # This just keeps the connection alive


class DeltaStreamProcessor:
    """
    Process delta streams for tool calls and content.
    """
    
    def __init__(self):
        self.content_buffer = []
        self.tool_call_buffer = {}
        self.current_tool_index = None
    
    def process_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a delta chunk.
        
        Args:
            delta: Delta from streaming response
            
        Returns:
            Processed delta with accumulated data
        """
        result = {}
        
        # Handle content delta
        if 'content' in delta and delta['content']:
            self.content_buffer.append(delta['content'])
            result['content'] = delta['content']
            result['accumulated_content'] = ''.join(self.content_buffer)
        
        # Handle tool call delta
        if 'tool_calls' in delta:
            for tool_call in delta['tool_calls']:
                index = tool_call.get('index', 0)
                
                if index not in self.tool_call_buffer:
                    self.tool_call_buffer[index] = {
                        'id': '',
                        'type': 'function',
                        'function': {
                            'name': '',
                            'arguments': ''
                        }
                    }
                
                # Accumulate tool call data
                if 'id' in tool_call:
                    self.tool_call_buffer[index]['id'] = tool_call['id']
                
                if 'function' in tool_call:
                    func = tool_call['function']
                    if 'name' in func:
                        self.tool_call_buffer[index]['function']['name'] = func['name']
                    if 'arguments' in func:
                        self.tool_call_buffer[index]['function']['arguments'] += func['arguments']
            
            # Return current state of tool calls
            result['tool_calls'] = list(self.tool_call_buffer.values())
        
        return result
    
    def get_final_result(self) -> Dict[str, Any]:
        """Get final accumulated result."""
        return {
            'content': ''.join(self.content_buffer),
            'tool_calls': list(self.tool_call_buffer.values()) if self.tool_call_buffer else None
        }
    
    def reset(self) -> None:
        """Reset buffers."""
        self.content_buffer.clear()
        self.tool_call_buffer.clear()
        self.current_tool_index = None


class WarpStreamAdapter:
    """
    Adapter for streaming to Warp terminal.
    """
    
    @staticmethod
    async def stream_to_warp_blocks(
        response_generator: AsyncGenerator[Dict[str, Any], None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Convert streaming response to Warp blocks.
        
        Args:
            response_generator: OpenAI-style streaming response
            
        Yields:
            Warp-formatted blocks
        """
        processor = DeltaStreamProcessor()
        
        async for chunk in response_generator:
            if 'choices' in chunk and chunk['choices']:
                delta = chunk['choices'][0].get('delta', {})
                processed = processor.process_delta(delta)
                
                # Create Warp block from delta
                blocks = []
                
                if 'content' in processed:
                    blocks.append({
                        'type': 'text',
                        'text': processed['content'],
                        'streaming': True
                    })
                
                if 'tool_calls' in processed:
                    for tool_call in processed['tool_calls']:
                        blocks.append({
                            'type': 'tool_call',
                            'tool': tool_call,
                            'streaming': True
                        })
                
                if blocks:
                    yield {'blocks': blocks, 'streaming': True}
        
        # Send final block
        final = processor.get_final_result()
        final_blocks = []
        
        if final['content']:
            final_blocks.append({
                'type': 'text',
                'text': final['content'],
                'streaming': False
            })
        
        if final['tool_calls']:
            for tool_call in final['tool_calls']:
                final_blocks.append({
                    'type': 'tool_call',
                    'tool': tool_call,
                    'streaming': False
                })
        
        if final_blocks:
            yield {'blocks': final_blocks, 'streaming': False, 'complete': True}


# Global instances
sse_streamer = SSEStreamer()
delta_processor = DeltaStreamProcessor()
warp_stream_adapter = WarpStreamAdapter()