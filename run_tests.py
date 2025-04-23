#!/usr/bin/env python3
"""
Script to run tests for the Poe Proxy MCP server.

This script discovers and runs all tests in the tests directory.
"""
import os
import sys
import unittest
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure POE_API_KEY is set for tests that need it
if not os.environ.get("POE_API_KEY"):
    print("Warning: POE_API_KEY environment variable is not set.")
    print("Some tests may fail. Set this in your .env file.")

def run_tests(pattern=None, verbose=False):
    """
    Run tests with the given pattern.
    
    Args:
        pattern: Pattern to match test files (default: test_*.py)
        verbose: Whether to show verbose output
    """
    # Add the parent directory to the path so tests can import modules
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    
    if pattern:
        suite = loader.discover("tests", pattern=pattern)
    else:
        suite = loader.discover("tests", pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests for the Poe Proxy MCP server")
    parser.add_argument("--pattern", help="Pattern to match test files (default: test_*.py)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    
    args = parser.parse_args()
    
    success = run_tests(args.pattern, args.verbose)
    
    sys.exit(0 if success else 1)