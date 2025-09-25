# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Tasks

### Environment Setup
```bash
# Quick setup using the installation script
./install.sh

# Manual setup
python -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -e .
cp .env.example .env
# Edit .env with your POE_API_KEY from https://poe.com/api_key
```

### Running the Server
```bash
# Standard mode (STDIO transport) - for MCP clients
poe-mcp
# or
python poe_server.py

# SSE mode - for web clients
poe-mcp-sse [port]
# or
python run_sse_server.py [port]  # defaults to port 8000

# Enhanced server with Warp agent integration
python enhanced_poe_server.py

# Phase 2 production server with full Warp integration
python poe_server_phase2.py
```

### Testing
```bash
# Run all tests
python run_tests.py

# Run tests with verbose output
python run_tests.py --verbose

# Run specific test pattern
python run_tests.py --pattern "test_poe*.py"

# Run a single test file directly
python -m pytest tests/test_poe_server.py -v
```

### Package Installation
```bash
# Install as editable package
pip install -e .

# Install from requirements
pip install -r requirements.txt
```

## Code Architecture

### Server Variants
The project has four main server implementations:

1. **`poe_server.py`** - Standard FastMCP server with basic POE proxy functionality
2. **`enhanced_poe_server.py`** - Extended version with Warp terminal integration for automatic action execution
3. **`poe_server_v2.py`** - SDK-compatible version designed for the official MCP Python SDK
4. **`poe_server_phase2.py`** - Production-ready server with full Warp integration, rate limiting, and OpenAI compatibility

### Core Components

#### MCP Tools Structure
All servers expose these core tools:
- `ask_poe` - Basic queries to POE models
- `ask_with_attachment` - File-based queries
- `clear_session` - Session management
- `list_available_models` - Model discovery
- `get_server_info` - Server configuration info

Enhanced server adds:
- `ask_poe_with_actions` - Queries with automatic terminal command execution
- `ask_with_attachment_and_actions` - File queries with action execution

Phase 2 server (`poe_server_phase2.py`) adds:
- `ask_poe_with_warp_context` - Queries with full Warp terminal context extraction
- `stream_poe_to_warp` - Real-time streaming responses with SSE format
- `execute_warp_action` - Execute terminal commands with safety validation
- `health_check` - Server health status endpoint
- `get_metrics` - Performance metrics and usage statistics
- `reset_metrics` - Reset collected metrics

#### Package Organization
```
poe_client/           # POE API client implementation
├── poe_api.py       # Core PoeClient class
├── session.py       # SessionManager for conversation context
├── claude_compat.py # Claude-specific formatting and protocol handling
├── file_utils.py    # File validation and processing utilities
├── rate_limiter.py  # Exponential backoff rate limiting with request queuing
├── streaming.py     # SSE streaming with delta content and error recovery
└── openai_client.py # OpenAI SDK-compatible client

utils/               # Shared utilities
├── config.py        # Configuration management using Pydantic
└── logging_utils.py # Logging setup and custom exception classes

warp_agent_tools.py  # Warp terminal integration tools
warp_context_handler.py # Phase 2 Warp context extraction and formatting
examples/            # Usage examples and web client
tests/               # Unit tests
```

#### Configuration Management
Uses Pydantic models for type-safe configuration:
- Environment variables loaded from `.env` file
- `PoeProxyConfig` class validates all settings
- Supports debug mode, Claude compatibility, file size limits, session expiry

#### Session Management
- Automatic session creation with UUID generation
- Message history maintained per session
- Configurable session expiry (default: 60 minutes)
- Thread-safe session operations

#### Claude Compatibility Layer
Special handling for Claude models:
- Thinking protocol support with configurable depth
- Automatic error recovery (retry without thinking on failure)
- Claude-specific response processing
- Model detection based on bot name patterns

#### Warp Agent Integration
The enhanced server includes:
- Command execution with safety checks
- File creation from model responses
- Editor integration (VS Code, vim, nano)
- Action parsing from POE model responses
- Structured results with success/error reporting

#### Phase 2 Production Features
The Phase 2 server (`poe_server_phase2.py`) provides:

**Rate Limiting & Reliability:**
- Exponential backoff with jitter (500 RPM limit)
- Request queuing with priority levels
- Automatic retry with `Retry-After` header support
- Circuit breaker pattern for failing endpoints

**Warp Terminal Context:**
- Extracts terminal output, selections, CWD, git state
- Processes environment variables and references
- Handles file attachments with multimodal support
- Formats output with Warp-specific blocks (commands, files, images, videos)

**Streaming Enhancements:**
- Server-Sent Events (SSE) format support
- Delta content streaming for incremental updates
- Chunk buffering and aggregation
- Stream error recovery and reconnection
- Real-time tool call streaming

**Production Readiness:**
- Health check endpoint with detailed status
- Comprehensive metrics collection (request count, latency, errors)
- Structured JSON logging with correlation IDs
- Graceful shutdown handling
- Resource cleanup on termination

### Security Considerations
- Basic command validation prevents dangerous operations (`rm -rf /`, etc.)
- File size limits enforced (configurable, default 10MB)
- Session expiry prevents indefinite memory usage
- Input validation using Pydantic models

### Error Handling
Custom exception hierarchy:
- `PoeProxyError` - Base exception
- `AuthenticationError` - API key issues
- `PoeApiError` - POE API failures
- `FileHandlingError` - File operation issues

All exceptions include structured error information and are logged appropriately.

## Development Patterns

### Adding New Tools
1. Define Pydantic models for request/response
2. Implement the tool function with `@mcp.tool()` decorator
3. Add comprehensive error handling
4. Include progress reporting for long operations
5. Update tests with both unit and integration coverage

### Model Integration
When adding support for new POE models:
1. Update model detection logic in `claude_compat.py` if special handling needed
2. Add model to the available models list
3. Test with both basic queries and file attachments
4. Document any model-specific quirks or requirements

### Testing Strategy
- Use mock objects for POE API calls to avoid API costs during testing
- Include both unit tests and integration tests
- Test error conditions and edge cases
- Verify session management works correctly
- Test file handling with various file types

### Transport Support
The server supports both STDIO and SSE transports:
- STDIO for command-line MCP clients
- SSE for web-based clients with the included HTML interface
- Both share the same core functionality with transport-specific entry points

## Environment Variables

Required:
- `POE_API_KEY` - Your POE API key from https://poe.com/api_key

Optional:
- `DEBUG_MODE` - Enable verbose logging (default: false)
- `USE_CLAUDE_COMPATIBLE` - Enable Claude compatibility mode (default: false)
- `MAX_FILE_SIZE_MB` - Maximum file upload size (default: 10)
- `SESSION_EXPIRY_MINUTES` - Session lifetime (default: 60)

Phase 2 Server Additional:
- `OPENAI_API_KEY` - OpenAI API key for SDK client (optional, uses POE if not set)
- `RATE_LIMIT_RPM` - Requests per minute limit (default: 500)
- `MAX_RETRIES` - Maximum retry attempts for failed requests (default: 3)
- `STREAM_BUFFER_SIZE` - SSE stream buffer size in KB (default: 64)
- `METRICS_ENABLED` - Enable metrics collection (default: true)
- `HEALTH_CHECK_INTERVAL` - Health check interval in seconds (default: 30)

## Bot Names
Standard bot names for POE models:
- `claude` - Claude models (automatically detects specific version)
- `gpt` - GPT models
- `o3` - OpenAI O3 models
- `gemini` - Google Gemini models
- `perplexity` - Perplexity models

The server maps these to the actual POE bot identifiers automatically.

## Phase 2 Usage Examples

### Query with Warp Context
```python
# The server automatically extracts context from Warp
result = await server.ask_poe_with_warp_context(
    prompt="Explain the current terminal state",
    model="claude",
    warp_context={  # Automatically provided by Warp
        "terminal_output": "...",
        "selected_text": "...",
        "cwd": "/path/to/project",
        "git_state": {...}
    }
)
```

### Streaming Response
```python
# Stream POE responses directly to Warp terminal
async for chunk in server.stream_poe_to_warp(
    prompt="Generate a Python script",
    model="gpt",
    stream=True
):
    # Chunks are formatted for Warp display
    print(chunk.delta_content)
```

### Execute Terminal Action
```python
# Execute commands extracted from POE responses
result = await server.execute_warp_action(
    action_type="command",
    content="ls -la",
    validate=True  # Safety validation enabled
)
```

### Health Monitoring
```python
# Check server health
health = await server.health_check()
print(f"Status: {health.status}")
print(f"Uptime: {health.uptime_seconds}s")
print(f"Active sessions: {health.active_sessions}")

# Get metrics
metrics = await server.get_metrics()
print(f"Total requests: {metrics.total_requests}")
print(f"Error rate: {metrics.error_rate:.2%}")
print(f"Avg latency: {metrics.avg_latency_ms}ms")
```
