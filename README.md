[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/anansitrading-poe-proxy-mcp-badge.png)](https://mseep.ai/app/anansitrading-poe-proxy-mcp)

# Enhanced POE MCP Server for Warp.dev

A production-ready Model Context Protocol (MCP) server that integrates POE (Poe.com API) with Warp.dev terminal, enabling AI-powered terminal assistance with context-aware tooling, automated workflows, and real-time streaming capabilities.

## 🚀 Features

### Core Capabilities
- **Multi-Model Support**: Access GPT-4o, Claude 3 Opus/Sonnet, Gemini Pro, Perplexity, and O3 models
- **Warp Terminal Integration**: Deep integration with Warp's context extraction and action execution
- **OpenAI SDK Compatibility**: Drop-in replacement for OpenAI API with POE backend
- **Production-Ready**: Rate limiting, health checks, metrics, and graceful shutdown

### Advanced Features
- **Context-Aware Queries**: Automatically extracts terminal output, selections, CWD, git state
- **Real-Time Streaming**: Server-Sent Events (SSE) with delta content streaming
- **Command Execution**: Safe execution of terminal commands with validation
- **File Operations**: Create and modify files directly from model responses
- **Session Management**: Maintain conversation context across multiple queries
- **Rate Limiting**: Exponential backoff with 500 RPM limit and request queuing
- **Health Monitoring**: Built-in health checks and Prometheus-style metrics

## 📋 Prerequisites

- **Operating System**: Linux (tested on Ubuntu, Zorin OS), macOS, or WSL2 on Windows
- **Python**: Version 3.8 or higher
- **Warp Terminal**: [Download from warp.dev](https://warp.dev/)
- **POE API Key**: Get yours from [poe.com/api_key](https://poe.com/api_key)

## 🔧 Installation

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Anansitrading/enhanced-poe-mcp.git
cd enhanced-poe-mcp

# Quick installation with script
chmod +x install.sh
./install.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -e .
```

### Step 2: Configure Environment

Create a `.env` file with your credentials:

```bash
# Required
POE_API_KEY=your_poe_api_key_here

# Optional (with defaults)
OPENAI_API_KEY=your_openai_key  # For OpenAI SDK compatibility
DEBUG_MODE=false
USE_CLAUDE_COMPATIBLE=true
MAX_FILE_SIZE_MB=10
SESSION_EXPIRY_MINUTES=60
RATE_LIMIT_RPM=500
MAX_RETRIES=3
STREAM_BUFFER_SIZE=64
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
```

### Step 3: Configure in Warp Terminal

1. **Open Warp MCP Settings**:
   - Navigate to: **Settings → AI → Manage MCP servers**
   - Or press `Ctrl+P` (Linux/Windows) or `Cmd+P` (macOS) and search for "Open MCP Servers"

2. **Add the POE MCP Server**:
   Click the **+ Add** button and paste this configuration:

   ```json
   {
     "enhanced-poe-mcp": {
       "command": "python3",
       "args": ["/home/david/Projects/Kijko/MVP/MVP_Kijko/enhanced-poe-mcp/poe_server_phase2.py"],
       "env": {
         "POE_API_KEY": "your_poe_api_key_here",
         "PYTHONUNBUFFERED": "1",
         "DEBUG_MODE": "false",
         "RATE_LIMIT_RPM": "500"
       }
     }
   }
   ```

   **Important**: Replace `/home/david/Projects/Kijko/MVP/MVP_Kijko/enhanced-poe-mcp` with your actual installation path.

3. **Save and Start**:
   - Click **Save** to add the configuration
   - Click **Start** next to your server entry
   - The server status should show as "Running"

## 🎮 Usage in Warp Terminal

### Basic POE Query
```bash
# Ask a simple question
@poe What is the fastest way to create a Python virtual environment?

# Expected output:
# POE will respond with: "Use `python -m venv <directory>` to create a virtual environment. 
# Activate it with `source <directory>/bin/activate` on Linux/macOS..."
```

### Query with File Attachment
```bash
# Review a configuration file
@poe Review this Dockerfile for security issues [attach:./Dockerfile]

# Expected output:
# POE analyzes the file and provides security recommendations:
# "Found potential issues: 1) Running as root user, 2) No health check defined..."
```

### Context-Aware Query
```bash
# Get help with a recent error (POE sees your terminal output)
@poe Why did my git push fail?

# Expected output:
# POE analyzes recent terminal output and responds:
# "The push failed because the remote has changes not in your local branch. 
# Run `git pull --rebase` first..."
```

### Execute Terminal Commands
```bash
# Let POE execute safe commands
@poe Find all Python files modified today and show their sizes

# Expected output:
# POE generates and executes: find . -name "*.py" -mtime 0 -ls
# Shows results directly in terminal
```

### Stream Long Responses
```bash
# Get streaming output for complex tasks
@poe Stream: Generate a complete FastAPI application with authentication

# Expected output:
# POE streams the code generation in real-time, showing each part as it's created
```

### Session Management
```bash
# Clear conversation context
@poe clear session

# Expected output:
# "Session cleared. Starting fresh conversation."
```

### List Available Models
```bash
# See all available AI models
@poe list models

# Expected output:
# Available models:
# - claude-3-opus: Advanced reasoning and analysis
# - gpt-4o: Latest GPT-4 variant
# - gemini-pro: Google's advanced model
# - perplexity: Web-aware responses
```

### Health Check
```bash
# Check server health
@poe health check

# Expected output:
# Server Status: Healthy ✓
# Uptime: 2h 34m
# Active Sessions: 3
# Request Rate: 45 RPM
```

## 🛠️ Advanced Configuration

### Server Variants

The project includes multiple server implementations for different use cases:

| Server File | Description | Use Case |
|------------|-------------|----------|
| `poe_server.py` | Basic MCP server | Simple POE proxy |
| `enhanced_poe_server.py` | Enhanced with Warp actions | Terminal automation |
| `poe_server_v2.py` | SDK-compatible | OpenAI SDK replacement |
| `poe_server_phase2.py` | Production server | Full features + monitoring |

### Running Different Modes

```bash
# Basic server
python poe_server.py

# Enhanced server with Warp integration
python enhanced_poe_server.py

# Production server (recommended)
python poe_server_phase2.py

# SSE mode for web clients
python run_sse_server.py [port]
```

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `POE_API_KEY` | Your POE API key | - | ✅ |
| `OPENAI_API_KEY` | OpenAI API key (for SDK mode) | - | ❌ |
| `DEBUG_MODE` | Enable verbose logging | `false` | ❌ |
| `USE_CLAUDE_COMPATIBLE` | Claude thinking protocol | `true` | ❌ |
| `MAX_FILE_SIZE_MB` | Max file upload size | `10` | ❌ |
| `SESSION_EXPIRY_MINUTES` | Session lifetime | `60` | ❌ |
| `RATE_LIMIT_RPM` | Requests per minute limit | `500` | ❌ |
| `MAX_RETRIES` | Retry attempts for failures | `3` | ❌ |
| `STREAM_BUFFER_SIZE` | SSE buffer size (KB) | `64` | ❌ |
| `METRICS_ENABLED` | Enable metrics collection | `true` | ❌ |
| `HEALTH_CHECK_INTERVAL` | Health check interval (seconds) | `30` | ❌ |

## 📊 Monitoring & Metrics

### Health Check Endpoint
```python
# Check server health programmatically
import requests
health = requests.get("http://localhost:8000/health")
print(health.json())
# Output: {"status": "healthy", "uptime": 3600, "active_sessions": 5}
```

### Metrics Endpoint
```python
# Get performance metrics
metrics = requests.get("http://localhost:8000/metrics")
print(metrics.json())
# Output: {"total_requests": 1234, "error_rate": 0.02, "avg_latency_ms": 250}
```

## 🐛 Troubleshooting

### MCP Server Won't Start in Warp

**Issue**: Server fails to start or shows as "Error" in Warp MCP panel

**Solutions**:
1. Verify Python path: `which python3` and update configuration
2. Check file permissions: `chmod +x poe_server_phase2.py`
3. Test manually: `cd /path/to/server && python3 poe_server_phase2.py`
4. Check logs: Look for errors in terminal output

### Authentication Errors

**Issue**: "Invalid API key" or "Authentication failed"

**Solutions**:
1. Verify POE_API_KEY in `.env` file
2. Ensure key is added to Warp MCP config environment
3. Test key at [poe.com/api_key](https://poe.com/api_key)

### Rate Limiting Issues

**Issue**: "Rate limit exceeded" errors

**Solutions**:
1. Increase `RATE_LIMIT_RPM` in configuration
2. Enable request queuing (automatic in Phase 2 server)
3. Implement exponential backoff in client code

### Context Not Working

**Issue**: POE doesn't see terminal output or context

**Solutions**:
1. Use `poe_server_phase2.py` (not basic server)
2. Ensure Warp context permissions are enabled
3. Update to latest Warp version

### Linux-Specific Issues

**Issue**: Permission denied or module not found

**Solutions**:
```bash
# Fix permissions
chmod -R 755 /path/to/enhanced-poe-mcp
chown -R $USER:$USER /path/to/enhanced-poe-mcp

# Install missing Python packages
pip install -r requirements.txt

# Use virtual environment
source venv/bin/activate
```

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────────────┐
│  Warp Terminal  │ ◄──────►│   POE MCP Server         │
│                 │  MCP     ├──────────────────────────┤
│  - User Input   │  Proto   │ • Request Handler        │
│  - Context      │         │ • Rate Limiter           │
│  - Actions      │         │ • Session Manager        │
└─────────────────┘         │ • Warp Context Handler   │
                            │ • Streaming Engine       │
                            └───────────┬──────────────┘
                                       │
                            ┌───────────▼──────────────┐
                            │      POE API             │
                            │                          │
                            │ • Claude, GPT-4o         │
                            │ • Gemini, Perplexity     │
                            └──────────────────────────┘
```

## 🧪 Testing

```bash
# Run all tests
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Test specific components
python -m pytest tests/test_poe_server.py -v
python -m pytest tests/test_rate_limiter.py -v
python -m pytest tests/test_streaming.py -v
```

## 📚 API Documentation

### MCP Tools Reference

| Tool | Description | Parameters |
|------|-------------|------------|
| `ask_poe` | Basic POE query | `prompt`, `model`, `session_id` |
| `ask_with_attachment` | Query with file | `prompt`, `model`, `file_path` |
| `ask_poe_with_warp_context` | Context-aware query | `prompt`, `model`, `warp_context` |
| `stream_poe_to_warp` | Streaming response | `prompt`, `model`, `stream=true` |
| `execute_warp_action` | Run terminal command | `action_type`, `content`, `validate` |
| `clear_session` | Reset conversation | `session_id` |
| `list_available_models` | Get model list | - |
| `health_check` | Server health | - |
| `get_metrics` | Performance stats | - |

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/Anansitrading/enhanced-poe-mcp.git
cd enhanced-poe-mcp
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run in development mode
DEBUG_MODE=true python poe_server_phase2.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Poe.com](https://poe.com) for the API access
- [Warp.dev](https://warp.dev) for the amazing terminal
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- The open-source community for continuous support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Anansitrading/enhanced-poe-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Anansitrading/enhanced-poe-mcp/discussions)
- **Documentation**: [Wiki](https://github.com/Anansitrading/enhanced-poe-mcp/wiki)

---

**Note**: This project is not affiliated with Poe.com or Warp.dev. It's an independent integration tool.