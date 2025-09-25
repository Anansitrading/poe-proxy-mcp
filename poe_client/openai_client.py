"""
OpenAI-compatible POE API client for dual-client architecture.

This module provides OpenAI SDK-based client for POE's new REST API endpoint,
supporting function calling, advanced parameters, and proper error handling.
"""
import os
import json
import time
import uuid
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from concurrent.futures import ThreadPoolExecutor
import httpx
import openai
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel, Field
from loguru import logger

from utils import (
    PoeProxyError,
    AuthenticationError,
    PoeApiError,
    handle_exception,
)


# Tool execution registry
TOOL_REGISTRY: Dict[str, callable] = {}


class OpenAITool(BaseModel):
    """OpenAI-compatible tool definition."""
    type: str = "function"
    function: Dict[str, Any]


class OpenAIMessage(BaseModel):
    """OpenAI-compatible message format."""
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class OpenAICompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    model: str
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = Field(None, ge=0, le=2)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    stream_options: Optional[Dict[str, Any]] = None
    user: Optional[str] = None


class PoeOpenAIClient:
    """
    OpenAI-compatible client for POE API.
    
    This client uses the OpenAI SDK to interact with POE's REST API,
    providing full support for function calling, streaming, and advanced parameters.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.poe.com/v1",
        async_mode: bool = True,
        debug_mode: bool = False
    ):
        """
        Initialize the OpenAI-compatible POE client.
        
        Args:
            api_key: POE API key
            base_url: Base URL for POE API (default: https://api.poe.com/v1)
            async_mode: Whether to use async client
            debug_mode: Enable debug logging
        """
        if not api_key:
            raise AuthenticationError(
                "POE API key is required. Get your API key from https://poe.com/api_key"
            )
        
        self.api_key = api_key
        self.base_url = base_url
        self.debug_mode = debug_mode
        
        # Initialize OpenAI clients
        if async_mode:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=60.0,
                max_retries=3,
            )
        else:
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=60.0,
                max_retries=3,
            )
        
        self.async_mode = async_mode
        logger.info(f"POE OpenAI client initialized (async={async_mode})")
    
    def register_tool(self, name: str, func: callable, description: str = "", parameters: Dict = None):
        """
        Register a tool for function calling.
        
        Args:
            name: Tool name
            func: Callable function
            description: Tool description
            parameters: JSON schema for parameters
        """
        TOOL_REGISTRY[name] = func
        logger.debug(f"Registered tool: {name}")
        
    def get_tool_definition(self, name: str, description: str, parameters: Dict) -> Dict:
        """
        Create OpenAI-compatible tool definition.
        
        Args:
            name: Tool name
            description: Tool description
            parameters: JSON schema for parameters
            
        Returns:
            OpenAI tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
    
    async def execute_tool_call(self, tool_call: Dict) -> Dict:
        """
        Execute a single tool call.
        
        Args:
            tool_call: Tool call from OpenAI response
            
        Returns:
            Tool execution result
        """
        name = tool_call["function"]["name"]
        try:
            args = json.loads(tool_call["function"]["arguments"])
            
            if name not in TOOL_REGISTRY:
                raise ValueError(f"Unknown tool: {name}")
            
            func = TOOL_REGISTRY[name]
            
            # Handle async and sync functions
            if asyncio.iscoroutinefunction(func):
                result = await func(**args)
            else:
                result = func(**args)
            
            return {
                "tool_call_id": tool_call["id"],
                "output": json.dumps(result) if not isinstance(result, str) else result
            }
        except Exception as e:
            logger.error(f"Tool execution failed for {name}: {str(e)}")
            return {
                "tool_call_id": tool_call["id"],
                "output": json.dumps({"error": str(e)})
            }
    
    async def process_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Process multiple tool calls, potentially in parallel.
        
        Args:
            tool_calls: List of tool calls from OpenAI response
            
        Returns:
            List of tool execution results
        """
        if not tool_calls:
            return []
        
        # Execute tool calls concurrently
        tasks = [self.execute_tool_call(call) for call in tool_calls]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        parallel_tool_calls: Optional[bool] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        stream: bool = False,
        stream_options: Optional[Dict[str, Any]] = None,
        user: Optional[str] = None,
        auto_execute_tools: bool = True,
    ) -> Union[Dict, AsyncGenerator]:
        """
        Create a chat completion with OpenAI-compatible API.
        
        Args:
            model: Model name (e.g., "Claude-Opus-4.1", "Gemini-2.5-Pro")
            messages: Conversation messages
            tools: Tool definitions
            tool_choice: Tool selection strategy
            parallel_tool_calls: Enable parallel tool execution
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2)
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            stream: Enable streaming response
            stream_options: Streaming configuration
            user: User identifier for sessions
            auto_execute_tools: Automatically execute tool calls
            
        Returns:
            Chat completion response or stream
        """
        try:
            # Build request parameters
            params = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            
            # Add optional parameters
            if tools:
                params["tools"] = tools
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
            if parallel_tool_calls is not None:
                params["parallel_tool_calls"] = parallel_tool_calls
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if temperature is not None:
                params["temperature"] = temperature
            if top_p is not None:
                params["top_p"] = top_p
            if stop is not None:
                params["stop"] = stop
            if stream_options:
                params["stream_options"] = stream_options
            if user:
                params["user"] = user
            
            if self.debug_mode:
                logger.debug(f"Chat completion request: model={model}, stream={stream}, tools={bool(tools)}")
            
            # Make the API call
            if self.async_mode:
                response = await self.client.chat.completions.create(**params)
            else:
                response = self.client.chat.completions.create(**params)
            
            # Handle streaming response
            if stream:
                return self._handle_stream(response)
            
            # Handle tool calls if present and auto-execution is enabled
            if auto_execute_tools and hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response.choices[0].message.tool_calls
                ]
                
                # Execute tools
                tool_results = await self.process_tool_calls(tool_calls)
                
                # Add tool results to messages
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["output"]
                    })
                
                # Make another call to get final response
                return await self.chat_completion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stop=stop,
                    stream=stream,
                    user=user,
                    auto_execute_tools=False  # Prevent infinite recursion
                )
            
            # Convert response to dict for compatibility
            return self._response_to_dict(response)
            
        except openai.AuthenticationError as e:
            raise AuthenticationError(f"POE API authentication failed: {str(e)}")
        except openai.RateLimitError as e:
            # Extract retry-after header if available
            retry_after = getattr(e, 'retry_after', None)
            raise PoeApiError(f"Rate limit exceeded. Retry after: {retry_after}")
        except openai.APIError as e:
            raise PoeApiError(f"POE API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {str(e)}")
            raise PoeProxyError(f"Chat completion failed: {str(e)}")
    
    async def _handle_stream(self, stream) -> AsyncGenerator:
        """Handle streaming response."""
        try:
            async for chunk in stream:
                yield {
                    "id": chunk.id,
                    "object": "chat.completion.chunk",
                    "created": chunk.created,
                    "model": chunk.model,
                    "choices": [
                        {
                            "index": choice.index,
                            "delta": {
                                "content": choice.delta.content,
                                "tool_calls": choice.delta.tool_calls if hasattr(choice.delta, 'tool_calls') else None
                            },
                            "finish_reason": choice.finish_reason
                        }
                        for choice in chunk.choices
                    ]
                }
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            raise PoeApiError(f"Streaming failed: {str(e)}")
    
    def _response_to_dict(self, response) -> Dict:
        """Convert OpenAI response object to dictionary."""
        return {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model,
            "choices": [
                {
                    "index": choice.index,
                    "message": {
                        "role": choice.message.role,
                        "content": choice.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in (choice.message.tool_calls or [])
                        ] if hasattr(choice.message, 'tool_calls') else None
                    },
                    "finish_reason": choice.finish_reason
                }
                for choice in response.choices
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if hasattr(response, 'usage') else None
        }
    
    @staticmethod
    def map_error_to_openai_format(error: Exception) -> Dict:
        """
        Map internal errors to OpenAI error format.
        
        Args:
            error: Exception to map
            
        Returns:
            OpenAI-compatible error response
        """
        error_mapping = {
            AuthenticationError: ("authentication_error", 401),
            PoeApiError: ("api_error", 500),
            ValueError: ("invalid_request_error", 400),
        }
        
        error_type, status_code = error_mapping.get(
            type(error), 
            ("internal_error", 500)
        )
        
        return {
            "error": {
                "message": str(error),
                "type": error_type,
                "code": status_code,
            }
        }


# Example tool implementations
def example_get_weather(city: str) -> Dict:
    """Example weather tool."""
    return {"weather": f"Sunny in {city}", "temperature": "72°F"}


def example_calculate(expression: str) -> Dict:
    """Example calculator tool."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


# Tool definitions for examples
EXAMPLE_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Perform mathematical calculation",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]