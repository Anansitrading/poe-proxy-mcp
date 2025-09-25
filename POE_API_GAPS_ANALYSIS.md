# POE API Gaps Analysis

## Executive Summary

After reviewing the updated POE API documentation, there are significant gaps between the current MCP server implementation and the newly available OpenAI-compatible API capabilities. The current implementation uses the legacy `fastapi_poe` SDK while POE now offers a full OpenAI-compatible REST API at `https://api.poe.com/v1`.

## Major Gaps and Unexposed Capabilities

### 1. **OpenAI-Compatible REST API** ⚠️ CRITICAL GAP
**Current State:** Using legacy `fastapi_poe` SDK
**New Capability:** Full OpenAI-compatible endpoint at `https://api.poe.com/v1/chat/completions`
**Impact:** Missing compatibility with thousands of existing OpenAI-based tools

**Recommended Implementation:**
```python
# New OpenAI-compatible client
import openai

class PoeOpenAIClient:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.poe.com/v1"
        )
```

### 2. **Tool Use / Function Calling** ⚠️ CRITICAL GAP
**Current State:** No function calling support
**New Capability:** Full support for:
- `tools` parameter
- `tool_choice` parameter  
- `parallel_tool_calls` parameter
- Tool call responses in completion

**Required MCP Tool Addition:**
```python
@mcp.tool()
async def ask_poe_with_tools(
    bot: str,
    prompt: str,
    tools: List[Dict[str, Any]],
    tool_choice: Optional[str] = "auto",
    parallel_tool_calls: bool = False
) -> Dict[str, Any]:
    """Query POE with function calling capabilities"""
```

### 3. **Advanced Model Parameters** 🔄 PARTIAL GAP
**Current State:** Basic prompt/response only
**New Capabilities:**
- `max_tokens` / `max_completion_tokens` - Token limit control
- `temperature` (0-2) - Response randomness control
- `top_p` - Nucleus sampling
- `stop` sequences - Custom stop sequences
- `stream_options` - Streaming configuration

**Required Enhancement:**
```python
class AdvancedQueryRequest(BaseModel):
    bot: str
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = Field(ge=0, le=2)
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    stream_options: Optional[Dict] = None
```

### 4. **Multi-Modal Support** ⚠️ CRITICAL GAP
**Current State:** Text and file attachments only
**New Capabilities:**
- Image generation models (GPT-Image-1)
- Video generation models (Veo-3)
- Audio generation models
- Recommendation: Use `stream=False` for media bots

**Required MCP Tools:**
```python
@mcp.tool()
async def generate_image(
    prompt: str,
    model: str = "GPT-Image-1",
    stream: bool = False
) -> Dict[str, Any]:
    """Generate images using POE image models"""

@mcp.tool()
async def generate_video(
    prompt: str,
    model: str = "Veo-3",
    stream: bool = False
) -> Dict[str, Any]:
    """Generate videos using POE video models"""
```

### 5. **New Model Names** 📝 UPDATE NEEDED
**Current State:** Older model names
**New Models Available:**
- Claude-Opus-4.1, Claude-Sonnet-4
- Gemini-2.5-Pro
- GPT-4.1
- Grok-4
- Llama-3.1-405B
- Veo-3 (video)
- GPT-Image-1 (image)

### 6. **Usage Tracking** 🔄 PARTIAL GAP
**Current State:** No token usage tracking
**New Capability:** Full usage statistics in responses:
- `completion_tokens`
- `prompt_tokens`
- `total_tokens`

### 7. **Error Handling Standards** 🔄 PARTIAL GAP
**Current State:** Custom error handling
**New Standard:** OpenAI-compatible error format with specific codes:
```json
{
  "error": {
    "code": 401,
    "type": "authentication_error",
    "message": "Invalid API key",
    "metadata": {...}
  }
}
```

### 8. **Rate Limiting** ⚠️ MISSING
**Current State:** No rate limit handling
**New Capability:** 500 RPM rate limit with retry headers
- Need to respect `Retry-After` header
- Implement exponential backoff starting at 250ms

### 9. **Streaming Enhancements** 🔄 PARTIAL GAP
**Current State:** Basic streaming support
**New Capabilities:**
- `stream_options` parameter
- Delta content streaming format
- Proper chunk handling for tool calls

### 10. **System Messages** ✅ SUPPORTED (Verify)
**Current State:** Unknown
**New Capability:** Full system message support in conversation

## Recommended Implementation Priority

### Phase 1: Critical Updates (Immediate)
1. **Add OpenAI-compatible client option** alongside existing `fastapi_poe`
2. **Implement function calling/tools support**
3. **Update model list** with new names
4. **Add multi-modal generation tools**

### Phase 2: Enhanced Features (Next Sprint)
1. **Add advanced parameters** (temperature, max_tokens, top_p, stop)
2. **Implement proper usage tracking**
3. **Standardize error handling** to match OpenAI format
4. **Add rate limit handling** with retry logic

### Phase 3: Complete Parity (Future)
1. **Full streaming options support**
2. **Response format handling** (when supported)
3. **Metadata and additional parameters**

## Migration Path

### Option 1: Dual Implementation
Maintain both implementations:
- Legacy: `fastapi_poe` for backward compatibility
- New: OpenAI-compatible for modern features

### Option 2: Full Migration
Replace `fastapi_poe` with OpenAI SDK:
- Pros: Simpler, standard interface, better tool compatibility
- Cons: Breaking change for existing users

## Code Example: OpenAI-Compatible Implementation

```python
# New poe_openai_client.py
import openai
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class PoeOpenAIClient:
    """OpenAI-compatible POE API client"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.poe.com/v1"
        )
    
    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """Create chat completion using OpenAI-compatible API"""
        
        params = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        # Add optional parameters
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if temperature is not None:
            params["temperature"] = temperature
        if top_p is not None:
            params["top_p"] = top_p
        if tools:
            params["tools"] = tools
        if tool_choice:
            params["tool_choice"] = tool_choice
            
        return await self.client.chat.completions.create(**params)
```

## Testing Requirements

1. **Compatibility Tests:** Verify OpenAI SDK works with POE endpoint
2. **Function Calling Tests:** Test tool use with various models
3. **Multi-Modal Tests:** Test image/video/audio generation
4. **Rate Limit Tests:** Verify retry logic and backoff
5. **Error Handling Tests:** Ensure proper error format mapping

## Backward Compatibility Considerations

- Maintain existing MCP tools for legacy users
- Add new tools with `_v2` suffix for OpenAI-compatible features
- Provide migration guide for users
- Support both API styles during transition period

## Conclusion

The current implementation is missing critical features available in POE's OpenAI-compatible API. The most impactful additions would be:

1. **OpenAI compatibility** - Enables use with existing tools
2. **Function calling** - Critical for agent workflows  
3. **Multi-modal support** - Image/video/audio generation
4. **Advanced parameters** - Better control over responses

Implementing these would significantly enhance the MCP server's capabilities and make it compatible with the broader OpenAI ecosystem.