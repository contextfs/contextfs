"""MCP Server module for ContextFS.

Provides HTTP/SSE-based MCP server for Claude Code, Gemini CLI, and other clients.
Uses FastMCP for cleaner implementation and better multi-client compatibility.
"""

from contextfs.mcp.fastmcp_server import create_mcp_app, run_mcp_server

__all__ = ["create_mcp_app", "run_mcp_server"]
