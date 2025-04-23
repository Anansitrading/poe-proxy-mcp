#!/usr/bin/env python3
"""
Configure MCP settings for Poe Proxy MCP server (SDK-Compatible Version).

This script helps users configure their MCP settings for the Poe Proxy MCP server,
ensuring proper Claude compatibility while preserving all existing MCP configurations.
"""
import os
import sys
import json
import argparse
from pathlib import Path

# Default MCP config paths
DEFAULT_MCP_CONFIG_PATHS = [
    os.path.expanduser("~/.codeium/windsurf/mcp_config.json"),
    os.path.expanduser("~/.config/mcp/config.json"),
    os.path.expanduser("~/.mcp/config.json"),
]


def find_mcp_config():
    """Find the MCP config file."""
    for path in DEFAULT_MCP_CONFIG_PATHS:
        if os.path.exists(path):
            return path
    return None


def load_mcp_config(config_path):
    """Load the MCP config file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading MCP config: {str(e)}")
        return None


def save_mcp_config(config_path, config):
    """Save the MCP config file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving MCP config: {str(e)}")
        return False


def configure_poe_mcp(config_path, server_name, port, env_vars, python_path=None, script_path=None):
    """
    Configure the Poe Proxy MCP server in the MCP config.
    
    IMPORTANT: This function will only add a new server entry or update an existing
    entry with the same name. It will NEVER modify any other existing MCP server settings.
    """
    # Load existing config or create new one
    if os.path.exists(config_path):
        config = load_mcp_config(config_path)
        if config is None:
            print(f"Could not load config from {config_path}. Creating new config.")
            config = {"mcpServers": {}}
    else:
        print(f"Config file {config_path} does not exist. Creating new config.")
        config = {"mcpServers": {}}
    
    # Ensure mcpServers key exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Get current directory if script_path is not provided
    if script_path is None:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(current_dir, "run_sse_server_v2.py")
    
    # Use system Python if python_path is not provided
    if python_path is None:
        python_path = sys.executable
    
    # Convert environment variables to dictionary
    env_dict = {}
    for var in env_vars:
        if "=" in var:
            key, value = var.split("=", 1)
            env_dict[key] = value
    
    # Create server config in Codeium MCP format
    server_config = {
        "command": python_path,
        "args": [script_path, str(port)],
        "env": env_dict,
        "disabled": False,
        "autoApprove": [
            "ask_poe",
            "ask_with_attachment",
            "clear_session",
            "list_available_models",
            "get_server_info"
        ]
    }
    
    # Add or update server in config
    if server_name in config["mcpServers"]:
        print(f"Updating existing server configuration for {server_name}")
    else:
        print(f"Adding new server configuration for {server_name}")
    
    config["mcpServers"][server_name] = server_config
    
    # Save config
    if save_mcp_config(config_path, config):
        print(f"Successfully configured {server_name} in {config_path}")
        print(f"Server will run on port {port}")
        print("Environment variables:")
        for key, value in server_config["env"].items():
            print(f"  {key}={value}")
        return True
    else:
        print(f"Failed to configure {server_name} in {config_path}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Configure MCP settings for Poe Proxy MCP server (SDK-Compatible Version)")
    parser.add_argument("--config", type=str, help="Path to MCP config file")
    parser.add_argument("--name", type=str, default="PoeMCP", help="Name for the MCP server (default: PoeMCP)")
    parser.add_argument("--port", type=int, default=8000, help="Port for the MCP server (default: 8000)")
    parser.add_argument("--env", type=str, action="append", default=[], 
                        help="Environment variables in the format KEY=VALUE (can be used multiple times)")
    parser.add_argument("--api-key", type=str, help="Poe API key (will be added as POE_API_KEY environment variable)")
    parser.add_argument("--python-path", type=str, help="Path to Python interpreter (default: current Python)")
    parser.add_argument("--script-path", type=str, help="Path to run_sse_server_v2.py script (default: auto-detect)")
    parser.add_argument("--sdk-compatible", action="store_true", help="Use the SDK-compatible implementation")
    
    args = parser.parse_args()
    
    # Find config path
    config_path = args.config
    if config_path is None:
        config_path = find_mcp_config()
        if config_path is None:
            # Use default path
            config_path = DEFAULT_MCP_CONFIG_PATHS[0]
            print(f"No existing MCP config found. Using default path: {config_path}")
    
    # Add API key to environment variables if provided
    env_vars = args.env.copy()
    if args.api_key:
        env_vars.append(f"POE_API_KEY={args.api_key}")
    
    # Add Claude compatibility by default if not specified
    if not any(var.startswith("CLAUDE_COMPATIBLE=") for var in env_vars):
        env_vars.append("CLAUDE_COMPATIBLE=true")
    
    # Add SDK compatibility flag if specified
    if args.sdk_compatible and not any(var.startswith("SDK_COMPATIBLE=") for var in env_vars):
        env_vars.append("SDK_COMPATIBLE=true")
    
    # Get script path
    script_path = args.script_path
    if script_path is None:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if args.sdk_compatible:
            script_path = os.path.join(current_dir, "run_sse_server_v2.py")
        else:
            script_path = os.path.join(current_dir, "run_sse_server.py")
    
    # Configure server
    configure_poe_mcp(
        config_path=config_path,
        server_name=args.name,
        port=args.port,
        env_vars=env_vars,
        python_path=args.python_path,
        script_path=script_path
    )
    
    print("\nConfiguration complete!")
    print("To use this server with Claude, make sure your MCP client is configured to use it.")
    print(f"The server will be available at: http://localhost:{args.port}")
    print("\nExample usage with FastMCP client:")
    print("```python")
    print("from mcp.client import MCPClient")
    print(f"client = MCPClient('http://localhost:{args.port}')")
    print("response = await client.call('ask_poe', {")
    print("    'bot': 'claude',")
    print("    'prompt': 'Hello, Claude!'")
    print("})")
    print("```")


if __name__ == "__main__":
    main()