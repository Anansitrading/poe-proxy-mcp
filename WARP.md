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
The project has three main server implementations:

1. **`poe_server.py`** - Standard FastMCP server with basic POE proxy functionality
2. **`enhanced_poe_server.py`** - Extended version with Warp terminal integration for automatic action execution
3. **`poe_server_v2.py`** - SDK-compatible version designed for the official MCP Python SDK

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

#### Package Organization
```
poe_client/           # POE API client implementation
├── poe_api.py       # Core PoeClient class
├── session.py       # SessionManager for conversation context
├── claude_compat.py # Claude-specific formatting and protocol handling
└── file_utils.py    # File validation and processing utilities

utils/               # Shared utilities
├── config.py        # Configuration management using Pydantic
└── logging_utils.py # Logging setup and custom exception classes

warp_agent_tools.py  # Warp terminal integration tools
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

## Bot Names
Standard bot names for POE models:
- `claude` - Claude models (automatically detects specific version)
- `gpt` - GPT models
- `o3` - OpenAI O3 models
- `gemini` - Google Gemini models
- `perplexity` - Perplexity models

The server maps these to the actual POE bot identifiers automatically.