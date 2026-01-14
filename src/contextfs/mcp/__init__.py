"""MCP Server module for ContextFS.

Provides HTTP/SSE-based MCP server for Claude Code and other clients.
"""

from contextfs.mcp.server import create_mcp_app, run_mcp_server

__all__ = ["create_mcp_app", "run_mcp_server"]
