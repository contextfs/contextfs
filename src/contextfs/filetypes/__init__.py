"""
ContextFS File Types Module

Provides type-safe file handling with:
- AST parsing for structured content extraction
- Relationship extraction between files
- Cross-reference linking
- Custom chunking and embedding strategies per file type
"""

from contextfs.filetypes.base import (
    FileTypeHandler,
    ParsedDocument,
    DocumentChunk,
    DocumentNode,
    NodeType,
    Relationship,
    RelationType,
    CrossReference,
    ChunkStrategy,
    SourceLocation,
)
from contextfs.filetypes.registry import FileTypeRegistry, get_handler
from contextfs.filetypes.linker import CrossReferenceLinker, RelationshipExtractor
from contextfs.filetypes.integration import SmartDocumentProcessor, RAGIntegration

__all__ = [
    # Base classes
    "FileTypeHandler",
    "ParsedDocument",
    "DocumentChunk",
    "DocumentNode",
    "NodeType",
    "Relationship",
    "RelationType",
    "CrossReference",
    "ChunkStrategy",
    "SourceLocation",
    # Registry
    "FileTypeRegistry",
    "get_handler",
    # Linker
    "CrossReferenceLinker",
    "RelationshipExtractor",
    # Integration
    "SmartDocumentProcessor",
    "RAGIntegration",
]
