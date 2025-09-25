#!/usr/bin/env python3
"""
POE MCP Server Phase 2 - Production-Ready with Warp Integration

Complete implementation with:
- Rate limiting and request queuing
- Warp terminal context extraction and output formatting
- Enhanced streaming with SSE support
- Health check endpoint
- Comprehensive metrics and logging
"""
import os
import sys
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from loguru import logger

# Import Phase 2 modules
from poe_client.rate_limiter import rate_limiter, with_rate_limit
from poe_client.streaming import (
    sse_streamer,
    warp_stream_adapter,
    DeltaStreamProcessor
)
from warp_context_handler import (
    warp_integration,
    WarpContextExtractor,
    WarpOutputFormatter,
    WarpActionExecutor
)

# Import existing modules
from poe_client.openai_client import PoeOpenAIClient
from utils import (
    setup_logging,
    get_config,
    handle_exception,
)

# Initialize configuration
config = get_config()
logger = setup_logging(config.debug_mode)

# Create FastMCP server
mcp = FastMCP("POE MCP Server Phase 2 - Warp Integrated")

# Initialize OpenAI client with rate limiting
openai_client = PoeOpenAIClient(
    api_key=config.poe_api_key,
    async_mode=True,
    debug_mode=config.debug_mode
)

# Production metrics
metrics = {
    'start_time': time.time(),
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'total_latency': 0.0,
    'total_tokens': 0,
    'warp_contexts_processed': 0,
    'commands_executed': 0,
    'files_created': 0,
}


class WarpContextRequest(BaseModel):
    """Request with Warp context."""
    bot: str = Field(description="Model name")
    prompt: str = Field(description="User prompt")
    context: Dict[str, Any] = Field(default_factory=dict, description="Warp context")
    priority: int = Field(default=5, ge=1, le=10, description="Request priority")
    stream: bool = Field(default=False, description="Enable streaming")
    execute_actions: bool = Field(default=True, description="Execute detected actions")
    max_tokens: Optional[int] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)


@mcp.tool()
async def ask_poe_with_warp_context(
    bot: str,
    prompt: str,
    context: Dict[str, Any],
    priority: int = 5,
    stream: bool = False,
    execute_actions: bool = True,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Query POE with full Warp context integration.
    
    This tool:
    1. Extracts context from Warp (terminal, git, files, etc.)
    2. Queries POE with rate limiting
    3. Formats response for Warp display
    4. Executes any detected actions
    
    Args:
        bot: Model name
        prompt: User prompt
        context: Warp context object
        priority: Request priority (1-10)
        stream: Enable streaming
        execute_actions: Execute detected actions
        max_tokens: Max tokens to generate
        temperature: Sampling temperature
        
    Returns:
        Warp-formatted response with blocks
    """
    start_time = time.time()
    metrics['total_requests'] += 1
    
    try:
        # Extract Warp context
        warp_context = WarpContextExtractor.extract_from_request(context)
        metrics['warp_contexts_processed'] += 1
        
        # Build enhanced prompt with context
        enhanced_prompt = _build_contextual_prompt(prompt, warp_context)
        
        # Prepare messages
        messages = [{"role": "user", "content": enhanced_prompt}]
        
        # Add git context if available
        if warp_context.get('git', {}).get('branch'):
            messages.insert(0, {
                "role": "system",
                "content": f"Working in git branch: {warp_context['git']['branch']}"
            })
        
        # Query POE with rate limiting
        if stream:
            # Streaming response
            response_generator = await with_rate_limit(
                openai_client.chat_completion,
                model=bot,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                priority=priority
            )
            
            # Convert to Warp blocks
            warp_blocks_generator = warp_stream_adapter.stream_to_warp_blocks(
                response_generator
            )
            
            return {
                "streaming": True,
                "generator": warp_blocks_generator,
                "context": warp_context
            }
        else:
            # Non-streaming response
            response = await with_rate_limit(
                openai_client.chat_completion,
                model=bot,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False,
                priority=priority
            )
            
            # Extract response text
            response_text = response['choices'][0]['message']['content']
            
            # Format for Warp
            warp_blocks = warp_integration.format_poe_response(response_text)
            
            # Execute actions if enabled
            action_results = []
            if execute_actions:
                action_results = await WarpActionExecutor.parse_and_execute_actions(
                    response_text,
                    warp_context
                )
                metrics['commands_executed'] += sum(
                    1 for r in action_results if r.get('command')
                )
                metrics['files_created'] += sum(
                    1 for r in action_results if r.get('filepath')
                )
            
            # Update metrics
            latency = time.time() - start_time
            metrics['total_latency'] += latency
            metrics['successful_requests'] += 1
            
            if response.get('usage'):
                metrics['total_tokens'] += response['usage'].get('total_tokens', 0)
            
            return {
                "blocks": warp_blocks,
                "context": warp_context,
                "actions": action_results,
                "usage": response.get('usage', {}),
                "latency": latency,
            }
            
    except Exception as e:
        metrics['failed_requests'] += 1
        logger.error(f"Warp context query failed: {e}")
        
        # Return error block
        error_block = WarpOutputFormatter.create_error_block(
            str(e),
            details=f"Model: {bot}, Priority: {priority}"
        )
        
        return {
            "blocks": [error_block.to_dict()],
            "error": str(e),
            "context": context
        }


@mcp.tool()
async def stream_poe_to_warp(
    bot: str,
    prompt: str,
    context: Dict[str, Any],
    priority: int = 5,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Stream POE response directly to Warp with SSE.
    
    Args:
        bot: Model name
        prompt: User prompt
        context: Warp context
        priority: Request priority
        max_tokens: Max tokens
        temperature: Sampling temperature
        
    Returns:
        SSE stream generator
    """
    try:
        # Extract context
        warp_context = WarpContextExtractor.extract_from_request(context)
        enhanced_prompt = _build_contextual_prompt(prompt, warp_context)
        
        messages = [{"role": "user", "content": enhanced_prompt}]
        
        # Get streaming response
        response_generator = await with_rate_limit(
            openai_client.chat_completion,
            model=bot,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            priority=priority
        )
        
        # Convert to SSE
        sse_generator = sse_streamer.stream_response(response_generator)
        
        return {
            "type": "sse_stream",
            "generator": sse_generator,
            "context": warp_context
        }
        
    except Exception as e:
        logger.error(f"Streaming failed: {e}")
        raise


@mcp.tool()
async def execute_warp_action(
    action_type: str,
    payload: Dict[str, Any],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a specific action in Warp terminal.
    
    Args:
        action_type: Type of action (command, file, etc.)
        payload: Action payload
        context: Warp context
        
    Returns:
        Action result
    """
    warp_context = WarpContextExtractor.extract_from_request(context)
    
    if action_type == "command":
        result = await WarpActionExecutor.execute_command(
            payload['command'],
            cwd=warp_context.get('cwd')
        )
        metrics['commands_executed'] += 1
        
    elif action_type == "file":
        result = await WarpActionExecutor.create_file(
            payload['filepath'],
            payload['content']
        )
        metrics['files_created'] += 1
        
    else:
        result = {"error": f"Unknown action type: {action_type}"}
    
    # Format result as Warp blocks
    if result.get('success'):
        blocks = [WarpOutputFormatter.create_text_block(
            f"✅ Action completed: {action_type}"
        ).to_dict()]
    else:
        blocks = [WarpOutputFormatter.create_error_block(
            f"Action failed: {result.get('error', 'Unknown error')}"
        ).to_dict()]
    
    return {"blocks": blocks, "result": result}


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with metrics.
    
    Returns comprehensive health status and metrics.
    """
    uptime = time.time() - metrics['start_time']
    
    # Get rate limiter metrics
    rate_limit_metrics = rate_limiter.get_metrics()
    
    # Calculate averages
    avg_latency = (
        metrics['total_latency'] / metrics['successful_requests']
        if metrics['successful_requests'] > 0 else 0
    )
    
    success_rate = (
        metrics['successful_requests'] / metrics['total_requests'] * 100
        if metrics['total_requests'] > 0 else 100
    )
    
    health_status = {
        "status": "healthy",
        "uptime_seconds": uptime,
        "uptime_formatted": _format_uptime(uptime),
        "metrics": {
            "requests": {
                "total": metrics['total_requests'],
                "successful": metrics['successful_requests'],
                "failed": metrics['failed_requests'],
                "success_rate": f"{success_rate:.2f}%",
            },
            "performance": {
                "average_latency_ms": avg_latency * 1000,
                "total_tokens": metrics['total_tokens'],
                "tokens_per_request": (
                    metrics['total_tokens'] / metrics['successful_requests']
                    if metrics['successful_requests'] > 0 else 0
                ),
            },
            "warp_integration": {
                "contexts_processed": metrics['warp_contexts_processed'],
                "commands_executed": metrics['commands_executed'],
                "files_created": metrics['files_created'],
            },
            "rate_limiting": rate_limit_metrics,
        },
        "configuration": {
            "debug_mode": config.debug_mode,
            "session_expiry_minutes": config.session_expiry_minutes,
            "rate_limit_rpm": 500,
        },
    }
    
    # Check for issues
    if success_rate < 50:
        health_status["status"] = "degraded"
        health_status["issues"] = ["Low success rate"]
    
    if rate_limit_metrics.get('rate_limited', 0) > 100:
        if "issues" not in health_status:
            health_status["issues"] = []
        health_status["issues"].append("High rate limiting")
    
    return health_status


@mcp.tool()
async def get_metrics() -> Dict[str, Any]:
    """Get detailed metrics."""
    return {
        **metrics,
        "rate_limiter": rate_limiter.get_metrics(),
        "timestamp": time.time(),
    }


@mcp.tool()
async def reset_metrics() -> Dict[str, str]:
    """Reset metrics counters."""
    global metrics
    metrics = {
        'start_time': time.time(),
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_latency': 0.0,
        'total_tokens': 0,
        'warp_contexts_processed': 0,
        'commands_executed': 0,
        'files_created': 0,
    }
    rate_limiter.reset_metrics()
    return {"status": "Metrics reset successfully"}


def _build_contextual_prompt(prompt: str, context: Dict[str, Any]) -> str:
    """Build enhanced prompt with Warp context."""
    parts = [prompt]
    
    # Add terminal output if available
    terminal_output = WarpContextExtractor.extract_terminal_output(
        context.get('blocks', [])
    )
    if terminal_output:
        parts.append(f"\n\nTerminal output:\n```\n{terminal_output[:1000]}\n```")
    
    # Add selected text
    selected = WarpContextExtractor.extract_selected_text(context)
    if selected:
        parts.append(f"\n\nSelected text:\n```\n{selected}\n```")
    
    # Add file references
    files = WarpContextExtractor.extract_file_references(context)
    if files:
        parts.append(f"\n\nReferenced files: {', '.join(files)}")
    
    return "\n".join(parts)


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "< 1m"


# Main entry point
if __name__ == "__main__":
    import sys
    import uvicorn
    
    logger.info("POE MCP Server Phase 2 starting...")
    logger.info(f"Rate limiting: 500 RPM with exponential backoff")
    logger.info(f"Warp integration: Context extraction and output formatting enabled")  
    logger.info(f"Streaming: SSE support with error recovery")
    logger.info(f"Starting server on port {os.getenv('PORT', 8000)}")
    
    # Run with uvicorn for production
    port = int(os.getenv('PORT', 8000))
    
    try:
        # Create FastAPI app from FastMCP
        app = mcp.get_app()
        
        # Run server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info" if config.debug_mode else "warning"
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
