#!/usr/bin/env python3
"""
Test script for OpenAI-compatible POE client.

This script tests the new OpenAI client implementation including:
- Basic chat completions
- Function calling
- Multi-modal generation
- Advanced parameters
- Error handling
"""
import os
import sys
import asyncio
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from poe_client.openai_client import (
    PoeOpenAIClient,
    example_get_weather,
    example_calculate,
    EXAMPLE_TOOL_DEFINITIONS,
)
from utils.config import get_config


async def test_basic_completion():
    """Test basic chat completion."""
    print("\n=== Testing Basic Completion ===")
    
    config = get_config()
    client = PoeOpenAIClient(
        api_key=config.poe_api_key,
        async_mode=True,
        debug_mode=True
    )
    
    response = await client.chat_completion(
        model="Claude-Sonnet-4",
        messages=[
            {"role": "user", "content": "What is 2+2? Answer in one word."}
        ],
        max_tokens=10,
        temperature=0.5,
    )
    
    print(f"Response: {response['choices'][0]['message']['content']}")
    print(f"Model: {response['model']}")
    if response.get('usage'):
        print(f"Tokens used: {response['usage']['total_tokens']}")
    
    return response


async def test_function_calling():
    """Test function calling."""
    print("\n=== Testing Function Calling ===")
    
    config = get_config()
    client = PoeOpenAIClient(
        api_key=config.poe_api_key,
        async_mode=True,
        debug_mode=True
    )
    
    # Register tools
    client.register_tool("get_weather", example_get_weather)
    client.register_tool("calculate", example_calculate)
    
    response = await client.chat_completion(
        model="GPT-4.1",
        messages=[
            {"role": "user", "content": "What's the weather in Paris and what is 15 * 3?"}
        ],
        tools=EXAMPLE_TOOL_DEFINITIONS,
        tool_choice="auto",
        auto_execute_tools=True,
    )
    
    print(f"Response: {response['choices'][0]['message']['content']}")
    if 'tool_calls' in response['choices'][0]['message']:
        print(f"Tools called: {len(response['choices'][0]['message']['tool_calls'])}")
    
    return response


async def test_streaming():
    """Test streaming response."""
    print("\n=== Testing Streaming ===")
    
    config = get_config()
    client = PoeOpenAIClient(
        api_key=config.poe_api_key,
        async_mode=True,
        debug_mode=True
    )
    
    stream = await client.chat_completion(
        model="Claude-Sonnet-4",
        messages=[
            {"role": "user", "content": "Count from 1 to 5 slowly."}
        ],
        stream=True,
    )
    
    print("Streaming response:")
    full_response = ""
    async for chunk in stream:
        if chunk['choices'][0]['delta'].get('content'):
            content = chunk['choices'][0]['delta']['content']
            print(content, end='', flush=True)
            full_response += content
    
    print("\n")
    return full_response


async def test_advanced_parameters():
    """Test advanced parameters."""
    print("\n=== Testing Advanced Parameters ===")
    
    config = get_config()
    client = PoeOpenAIClient(
        api_key=config.poe_api_key,
        async_mode=True,
        debug_mode=True
    )
    
    # Test with high temperature for creativity
    response1 = await client.chat_completion(
        model="Gemini-2.5-Pro",
        messages=[
            {"role": "user", "content": "Write a creative one-line story."}
        ],
        temperature=1.5,
        max_tokens=50,
        top_p=0.9,
    )
    
    print(f"High temp response: {response1['choices'][0]['message']['content']}")
    
    # Test with low temperature for determinism
    response2 = await client.chat_completion(
        model="Gemini-2.5-Pro",
        messages=[
            {"role": "user", "content": "What is the capital of France? One word only."}
        ],
        temperature=0.1,
        max_tokens=10,
    )
    
    print(f"Low temp response: {response2['choices'][0]['message']['content']}")
    
    return response1, response2


async def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")
    
    try:
        # Test with invalid API key
        client = PoeOpenAIClient(
            api_key="invalid_key",
            async_mode=True,
        )
        
        response = await client.chat_completion(
            model="Claude-Sonnet-4",
            messages=[{"role": "user", "content": "test"}],
        )
    except Exception as e:
        print(f"Expected error caught: {type(e).__name__}: {str(e)}")
        
        # Test error mapping
        error_dict = PoeOpenAIClient.map_error_to_openai_format(e)
        print(f"OpenAI error format: {json.dumps(error_dict, indent=2)}")
    
    return True


async def test_multi_modal():
    """Test multi-modal generation (image/video)."""
    print("\n=== Testing Multi-Modal Generation ===")
    
    config = get_config()
    client = PoeOpenAIClient(
        api_key=config.poe_api_key,
        async_mode=True,
        debug_mode=True
    )
    
    # Test image generation
    print("Testing image generation...")
    try:
        response = await client.chat_completion(
            model="GPT-Image-1",
            messages=[
                {"role": "user", "content": "A beautiful sunset over mountains"}
            ],
            stream=False,  # Media bots should use stream=False
        )
        
        print(f"Image response received (length: {len(response['choices'][0]['message']['content'])})")
    except Exception as e:
        print(f"Image generation error: {e}")
    
    return True


async def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("OpenAI-Compatible POE Client Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Completion", test_basic_completion),
        ("Function Calling", test_function_calling),
        ("Streaming", test_streaming),
        ("Advanced Parameters", test_advanced_parameters),
        ("Error Handling", test_error_handling),
        ("Multi-Modal", test_multi_modal),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = "✅ PASSED"
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            results[name] = f"❌ FAILED: {str(e)}"
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    for name, status in results.items():
        print(f"{name}: {status}")
    
    return results


if __name__ == "__main__":
    # Check for API key
    config = get_config()
    if not config.poe_api_key:
        print("Error: POE_API_KEY not set in environment or .env file")
        sys.exit(1)
    
    # Run tests
    asyncio.run(run_all_tests())