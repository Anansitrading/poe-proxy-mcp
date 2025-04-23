#!/usr/bin/env python3
"""
Setup script for the Poe Proxy MCP server.

This script allows the server to be installed using pip:
    pip install -e .
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="poe-proxy-mcp",
    version="0.1.0",
    author="Anansi Trading",
    author_email="info@anansitrading.com",
    description="A FastMCP server that proxies the Poe.com API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Anansitrading/poe-proxy-mcp",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastmcp>=0.2.0",
        "fastapi-poe>=0.0.16",
        "httpx>=0.24.1",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "loguru>=0.7.0",
        "uvicorn>=0.22.0",
        "python-multipart>=0.0.6",
    ],
    entry_points={
        "console_scripts": [
            "poe-mcp=poe_server:main",
            "poe-mcp-sse=run_sse_server:main",
        ],
    },
)