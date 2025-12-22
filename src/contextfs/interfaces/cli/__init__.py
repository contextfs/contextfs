"""
ContextFS CLI Package.

Command-line interface for ContextFS memory operations.

Usage:
    contextfs --help
    contextfs save "content" --type fact
    contextfs search "query"
"""

# Re-export from main CLI module for backward compatibility
# The CLI is still in contextfs.cli for now, this package provides
# the organizational structure for future splitting
from contextfs.cli import app, console, get_ctx

__all__ = ["app", "console", "get_ctx"]
