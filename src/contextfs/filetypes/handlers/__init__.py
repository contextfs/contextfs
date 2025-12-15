"""
File type handlers for various file formats.
"""

from contextfs.filetypes.handlers.python import PythonHandler
from contextfs.filetypes.handlers.latex import LaTeXHandler
from contextfs.filetypes.handlers.sql import SQLHandler
from contextfs.filetypes.handlers.markdown import MarkdownHandler
from contextfs.filetypes.handlers.javascript import JavaScriptHandler
from contextfs.filetypes.handlers.config import JSONHandler, YAMLHandler, TOMLHandler
from contextfs.filetypes.handlers.generic import GenericTextHandler

__all__ = [
    "PythonHandler",
    "LaTeXHandler",
    "SQLHandler",
    "MarkdownHandler",
    "JavaScriptHandler",
    "JSONHandler",
    "YAMLHandler",
    "TOMLHandler",
    "GenericTextHandler",
]
