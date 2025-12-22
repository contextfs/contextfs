"""
ContextFS MCP Server Package.

Model Context Protocol server for Claude Desktop and Claude Code integration.

Usage:
    contextfs serve  # Start MCP server
"""

# Re-export from main MCP module for backward compatibility
# The MCP server is still in contextfs.mcp_server for now
from contextfs.mcp_server import get_ctx, main, run_server

__all__ = ["main", "run_server", "get_ctx"]
