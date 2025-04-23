# Poe Proxy MCP Server Deployment Guide

This guide provides instructions for deploying the Poe Proxy MCP server in a production environment using native Python deployment (without containers) to ensure full Claude 3.7 compatibility.

## Why Native Python Deployment?

Container-based deployments (like Docker) can cause compatibility issues with Claude 3.7 Sonnet due to the isolation they create. These issues include:

1. Problems with the thinking protocol
2. Connection and context management issues
3. API authentication challenges
4. Reduced performance due to container overhead

By using a native Python deployment, we ensure direct access to the host system resources and avoid these compatibility issues.

## Prerequisites

- Python 3.8 or higher
- A Poe API key (get one from [Poe.com](https://poe.com/api_key))
- A Linux server (for systemd service deployment)
- Sudo/root access (for systemd service installation)

## Deployment Options

### Option 1: Direct Python Deployment (Recommended for Claude Compatibility)

1. Clone the repository:
   ```bash
   git clone https://github.com/Anansitrading/poe-proxy-mcp.git
   cd poe-proxy-mcp
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

3. Create a `.env` file with your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your Poe API key and other settings
   ```

4. Run the server:
   ```bash
   # For STDIO transport (CLI usage)
   python poe_server.py
   
   # For SSE transport (web client usage)
   python run_sse_server.py
   ```

### Option 2: Systemd Service (Recommended for Production)

1. Follow steps 1-3 from Option 1.

2. Edit the provided systemd service file:
   ```bash
   cp poe-proxy-mcp.service /tmp/poe-proxy-mcp.service
   nano /tmp/poe-proxy-mcp.service
   ```
   
   Update the following fields:
   - `User`: Your system username
   - `WorkingDirectory`: Absolute path to the project directory
   - `ExecStart`: Absolute path to the Python executable in your virtual environment
   - Environment variables: Set your Poe API key and other configuration

3. Install the systemd service:
   ```bash
   sudo mv /tmp/poe-proxy-mcp.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable poe-proxy-mcp.service
   sudo systemctl start poe-proxy-mcp.service
   ```

4. Check the service status:
   ```bash
   sudo systemctl status poe-proxy-mcp.service
   ```

### Option 3: Supervisor (Alternative to Systemd)

1. Follow steps 1-3 from Option 1.

2. Install supervisor:
   ```bash
   sudo apt-get install supervisor  # For Debian/Ubuntu
   # or
   sudo yum install supervisor  # For CentOS/RHEL
   ```

3. Create a supervisor configuration file:
   ```bash
   sudo nano /etc/supervisor/conf.d/poe-proxy-mcp.conf
   ```
   
   Add the following content:
   ```ini
   [program:poe-proxy-mcp]
   command=/path/to/poe-proxy-mcp/venv/bin/python /path/to/poe-proxy-mcp/run_sse_server.py
   directory=/path/to/poe-proxy-mcp
   user=your_username
   autostart=true
   autorestart=true
   environment=POE_API_KEY="your_api_key_here",CLAUDE_COMPATIBLE="true",DEBUG_MODE="false"
   stdout_logfile=/var/log/poe-proxy-mcp.log
   stderr_logfile=/var/log/poe-proxy-mcp.err
   ```

4. Update supervisor and start the service:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start poe-proxy-mcp
   ```

## Security Considerations

1. **API Key Security**: Store your Poe API key securely in the `.env` file or environment variables, never hardcode it.

2. **Network Security**: If exposing the server to the internet, use a reverse proxy (like Nginx) with HTTPS.

3. **User Permissions**: Run the service as a non-root user with minimal permissions.

4. **Rate Limiting**: Be aware of Poe's rate limits and implement appropriate error handling.

## Monitoring and Maintenance

1. **Logging**: Check logs for errors and issues:
   ```bash
   # For systemd service
   sudo journalctl -u poe-proxy-mcp.service
   
   # For supervisor
   sudo tail -f /var/log/poe-proxy-mcp.log
   ```

2. **Updating**: To update the server:
   ```bash
   cd /path/to/poe-proxy-mcp
   git pull
   source venv/bin/activate
   pip install -e .
   
   # Restart the service
   sudo systemctl restart poe-proxy-mcp.service  # For systemd
   # or
   sudo supervisorctl restart poe-proxy-mcp  # For supervisor
   ```

## Troubleshooting Claude Compatibility Issues

If you encounter issues with Claude compatibility:

1. Ensure `CLAUDE_COMPATIBLE=true` is set in your environment.

2. Check that the server has direct network access (not through a proxy).

3. Verify that your Poe API key has access to Claude models.

4. Try running the server directly (not as a service) to debug any issues:
   ```bash
   source venv/bin/activate
   DEBUG_MODE=true CLAUDE_COMPATIBLE=true POE_API_KEY=your_key python poe_server.py
   ```

5. Check the logs for any specific error messages related to Claude API calls.

## Conclusion

Native Python deployment is the recommended approach for the Poe Proxy MCP server, especially when working with Claude 3.7 Sonnet. This approach avoids the isolation issues that can occur with containerized deployments and ensures the best compatibility with Claude's thinking protocol and other features.