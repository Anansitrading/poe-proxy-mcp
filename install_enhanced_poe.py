#!/usr/bin/env python3
"""
Installation script for Enhanced POE MCP Server with Warp Integration

This script sets up the enhanced POE MCP server in your Warp configuration.
"""
import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional


def find_warp_config() -> Optional[str]:
    """Find the Warp MCP configuration file."""
    possible_paths = [
        Path.home() / ".warp" / "mcp_config.json",
        Path.home() / ".config" / "warp" / "mcp.json",
        Path.home() / ".warp" / "config" / "mcp.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # Return default path if none found
    return str(Path.home() / ".warp" / "mcp_config.json")


def load_config(config_path: str) -> Dict[str, Any]:
    """Load existing configuration or create new one."""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in {config_path}, creating new config")
    
    return {"mcpServers": {}}


def save_config(config_path: str, config: Dict[str, Any]) -> bool:
    """Save configuration file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False


def setup_enhanced_poe_server(
    config_path: str,
    server_name: str = "EnhancedPOE",
    poe_api_key: Optional[str] = None,
    enable_claude_compat: bool = True,
    enable_debug: bool = False,
    python_path: Optional[str] = None,
    server_script: Optional[str] = None,
) -> bool:
    """Set up the enhanced POE MCP server in Warp configuration."""
    
    # Load existing configuration
    config = load_config(config_path)
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Determine paths
    if python_path is None:
        python_path = sys.executable
    
    if server_script is None:
        server_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "enhanced_poe_server.py"))
    
    # Environment variables
    env_vars = {}
    
    if poe_api_key:
        env_vars["POE_API_KEY"] = poe_api_key
    
    if enable_claude_compat:
        env_vars["CLAUDE_COMPATIBLE"] = "true"
    
    if enable_debug:
        env_vars["DEBUG_MODE"] = "true"
    
    # Server configuration
    server_config = {
        "command": python_path,
        "args": [server_script],
        "env": env_vars,
        "autoApprove": [
            "ask_poe_with_actions",
            "ask_with_attachment_and_actions", 
            "execute_command_tool",
            "create_file_tool",
            "ask_poe",
            "ask_with_attachment",
            "clear_session",
            "list_available_models",
            "get_enhanced_server_info"
        ]
    }
    
    # Add to configuration
    config["mcpServers"][server_name] = server_config
    
    # Save configuration
    if save_config(config_path, config):
        print(f"✓ Enhanced POE MCP server configured as '{server_name}'")
        print(f"  Config file: {config_path}")
        print(f"  Server script: {server_script}")
        print(f"  Python: {python_path}")
        
        if env_vars:
            print("  Environment variables:")
            for key, value in env_vars.items():
                if key == "POE_API_KEY":
                    print(f"    {key}=***")
                else:
                    print(f"    {key}={value}")
        
        return True
    else:
        print("✗ Failed to save configuration")
        return False


def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    print("Checking dependencies...")
    
    required_modules = [
        "pydantic",
        "loguru", 
        "fastmcp",
        "httpx",
        "python-dotenv"
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module.replace("-", "_"))
            print(f"  ✓ {module}")
        except ImportError:
            missing.append(module)
            print(f"  ✗ {module}")
    
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    return True


def test_server_startup() -> bool:
    """Test if the server can start up properly."""
    print("Testing server startup...")
    
    try:
        # Try to import the enhanced server
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Basic import test
        import enhanced_poe_server
        print("  ✓ Server module imports successfully")
        
        # Check if POE API key is available
        poe_key = os.getenv("POE_API_KEY")
        if poe_key:
            print("  ✓ POE_API_KEY environment variable found")
        else:
            print("  ⚠ POE_API_KEY not found - server will fail without it")
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Server import failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Server test failed: {e}")
        return False


def main():
    """Main installation function."""
    parser = argparse.ArgumentParser(description="Install Enhanced POE MCP Server with Warp Integration")
    
    parser.add_argument("--config", type=str, help="Path to Warp MCP config file")
    parser.add_argument("--name", type=str, default="EnhancedPOE", help="Server name in config")
    parser.add_argument("--api-key", type=str, help="POE API key")
    parser.add_argument("--claude-compat", action="store_true", default=True, help="Enable Claude compatibility")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--python", type=str, help="Python executable path")
    parser.add_argument("--server", type=str, help="Server script path")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency checks")
    
    args = parser.parse_args()
    
    print("Enhanced POE MCP Server Installation")
    print("=" * 40)
    
    # Check dependencies unless skipped
    if not args.skip_checks:
        if not check_dependencies():
            print("\nPlease install missing dependencies first.")
            return 1
        
        if not test_server_startup():
            print("\nServer startup test failed. Please check your installation.")
            return 1
    
    # Find configuration path
    config_path = args.config or find_warp_config()
    print(f"\nUsing config file: {config_path}")
    
    # Get API key if not provided
    api_key = args.api_key
    if not api_key:
        api_key = os.getenv("POE_API_KEY")
    
    if not api_key:
        api_key = input("Enter your POE API key (get from https://poe.com/api_key): ").strip()
    
    if not api_key:
        print("POE API key is required for the server to function.")
        return 1
    
    # Set up the server
    success = setup_enhanced_poe_server(
        config_path=config_path,
        server_name=args.name,
        poe_api_key=api_key,
        enable_claude_compat=args.claude_compat,
        enable_debug=args.debug,
        python_path=args.python,
        server_script=args.server,
    )
    
    if success:
        print("\n" + "=" * 50)
        print("✓ Enhanced POE MCP Server installed successfully!")
        print("\nNext steps:")
        print("1. Restart Warp terminal")
        print("2. The server should appear in your MCP settings")
        print("3. Test with: ask_poe_with_actions")
        print("\nAvailable tools:")
        print("  • ask_poe_with_actions - Query POE models with automatic action execution")
        print("  • ask_with_attachment_and_actions - Query with file + actions")
        print("  • execute_command_tool - Execute terminal commands directly")  
        print("  • create_file_tool - Create files directly")
        print("  • All original POE MCP tools")
        
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())