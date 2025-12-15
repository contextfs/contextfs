"""
Cross-reference linker and relationship extractor.

Resolves relationships between documents:
- Import/require statements
- Type references and inheritance
- Foreign key relationships
- Document links and citations
"""

from pathlib import Path
from typing import Optional
from collections import defaultdict
import logging

from pydantic import BaseModel, Field

from contextfs.filetypes.base import (
    ParsedDocument,
    Relationship,
    RelationType,
    CrossReference,
    NodeType,
)

logger = logging.getLogger(__name__)


class DocumentIndex(BaseModel):
    """Index of documents for fast lookup."""

    documents: dict[str, ParsedDocument] = Field(default_factory=dict)
    symbols: dict[str, list[tuple[str, str]]] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)

    def add(self, doc: ParsedDocument) -> None:
        """Add document to index."""
        self.documents[doc.id] = doc
        self.paths[doc.file_path] = doc.id

        # Index symbols
        for name, node in doc.symbols.items():
            if name not in self.symbols:
                self.symbols[name] = []
            self.symbols[name].append((doc.id, node.id))

    def get_by_path(self, path: str) -> Optional[ParsedDocument]:
        """Get document by file path."""
        doc_id = self.paths.get(path)
        return self.documents.get(doc_id) if doc_id else None

    def get_by_id(self, doc_id: str) -> Optional[ParsedDocument]:
        """Get document by ID."""
        return self.documents.get(doc_id)

    def find_symbol(self, name: str) -> list[tuple[str, str]]:
        """Find all documents containing a symbol."""
        return self.symbols.get(name, [])


class RelationshipExtractor:
    """Extracts and aggregates relationships from documents."""

    def __init__(self):
        self.index = DocumentIndex()
        self.relationships: list[Relationship] = []
        self._by_source: dict[str, list[Relationship]] = defaultdict(list)
        self._by_target: dict[str, list[Relationship]] = defaultdict(list)
        self._by_type: dict[RelationType, list[Relationship]] = defaultdict(list)

    def add_document(self, doc: ParsedDocument) -> list[Relationship]:
        """Add document and extract its relationships."""
        self.index.add(doc)

        # Get handler to extract relationships
        from contextfs.filetypes.registry import get_handler

        handler = get_handler(doc.file_path)
        if handler:
            rels = handler.extract_relationships(doc)
            for rel in rels:
                self._add_relationship(rel)
            return rels
        return []

    def _add_relationship(self, rel: Relationship) -> None:
        """Add relationship to indexes."""
        self.relationships.append(rel)
        self._by_source[rel.source_document_id].append(rel)
        if rel.target_document_id:
            self._by_target[rel.target_document_id].append(rel)
        self._by_type[rel.type].append(rel)

    def get_outgoing(self, doc_id: str) -> list[Relationship]:
        """Get all relationships from a document."""
        return self._by_source.get(doc_id, [])

    def get_incoming(self, doc_id: str) -> list[Relationship]:
        """Get all relationships to a document."""
        return self._by_target.get(doc_id, [])

    def get_by_type(self, rel_type: RelationType) -> list[Relationship]:
        """Get relationships by type."""
        return self._by_type.get(rel_type, [])

    def get_import_graph(self) -> dict[str, list[str]]:
        """Build import dependency graph."""
        graph: dict[str, list[str]] = defaultdict(list)

        for rel in self._by_type.get(RelationType.IMPORTS, []):
            if rel.target_document_id:
                graph[rel.source_document_id].append(rel.target_document_id)

        return dict(graph)

    def get_inheritance_tree(self) -> dict[str, list[str]]:
        """Build class inheritance tree."""
        tree: dict[str, list[str]] = defaultdict(list)

        for rel in self._by_type.get(RelationType.INHERITS, []):
            if rel.target_name:
                # Find parent class
                matches = self.index.find_symbol(rel.target_name)
                for doc_id, node_id in matches:
                    tree[rel.source_name or ""].append(rel.target_name)

        return dict(tree)

    def find_usages(self, symbol_name: str) -> list[Relationship]:
        """Find all usages of a symbol."""
        usages = []

        for rel in self.relationships:
            if rel.target_name == symbol_name:
                usages.append(rel)

        return usages

    def to_dict(self) -> dict:
        """Export relationships as dictionary."""
        return {
            "total": len(self.relationships),
            "by_type": {
                rel_type.value: len(rels)
                for rel_type, rels in self._by_type.items()
            },
            "relationships": [rel.model_dump() for rel in self.relationships],
        }


class CrossReferenceLinker:
    """Links cross-references between documents."""

    def __init__(self, extractor: Optional[RelationshipExtractor] = None):
        self.extractor = extractor or RelationshipExtractor()
        self.cross_references: list[CrossReference] = []
        self._resolved: dict[str, CrossReference] = {}

    @property
    def index(self) -> DocumentIndex:
        """Access document index."""
        return self.extractor.index

    def add_document(self, doc: ParsedDocument) -> None:
        """Add document and extract relationships."""
        self.extractor.add_document(doc)

    def add_documents(self, docs: list[ParsedDocument]) -> None:
        """Add multiple documents."""
        for doc in docs:
            self.add_document(doc)

    def link_all(self) -> list[CrossReference]:
        """Resolve all cross-references."""
        self.cross_references = []
        self._resolved = {}

        for rel in self.extractor.relationships:
            xref = self._resolve_relationship(rel)
            if xref and xref.id not in self._resolved:
                self.cross_references.append(xref)
                self._resolved[xref.id] = xref

        return self.cross_references

    def _resolve_relationship(self, rel: Relationship) -> Optional[CrossReference]:
        """Resolve a relationship to a cross-reference."""
        # Try to find target document
        target_doc_id = rel.target_document_id
        target_node_id = rel.target_node_id

        if not target_doc_id and rel.target_name:
            target_doc_id, target_node_id = self._find_target(rel)

        if not target_doc_id:
            return None

        return CrossReference(
            source_document_id=rel.source_document_id,
            source_node_id=rel.source_node_id,
            target_document_id=target_doc_id,
            target_node_id=target_node_id,
            reference_type=rel.type.value,
            context=rel.context,
            location=rel.location,
            resolved=True,
        )

    def _find_target(self, rel: Relationship) -> tuple[Optional[str], Optional[str]]:
        """Find target document and node for a relationship."""
        target_name = rel.target_name
        if not target_name:
            return None, None

        # Handle different relationship types
        if rel.type == RelationType.IMPORTS:
            return self._resolve_import(rel)
        elif rel.type == RelationType.INHERITS:
            return self._resolve_inheritance(rel)
        elif rel.type == RelationType.LINKS_TO:
            return self._resolve_link(rel)
        elif rel.type == RelationType.REFERENCES:
            return self._resolve_reference(rel)
        elif rel.type == RelationType.FOREIGN_KEY:
            return self._resolve_foreign_key(rel)
        elif rel.type == RelationType.CITES:
            return self._resolve_citation(rel)

        # Default: symbol lookup
        matches = self.index.find_symbol(target_name)
        if matches:
            return matches[0]

        return None, None

    def _resolve_import(self, rel: Relationship) -> tuple[Optional[str], Optional[str]]:
        """Resolve import statement to target document."""
        target_name = rel.target_name or ""
        is_relative = rel.attributes.get("is_relative", False)

        if is_relative:
            # Resolve relative path
            source_doc = self.index.get_by_id(rel.source_document_id)
            if source_doc:
                source_dir = Path(source_doc.file_path).parent
                target_path = self._resolve_module_path(source_dir, target_name)
                if target_path:
                    target_doc = self.index.get_by_path(str(target_path))
                    if target_doc:
                        return target_doc.id, None

        # Try to find by module name
        for path, doc_id in self.index.paths.items():
            if self._path_matches_module(path, target_name):
                return doc_id, None

        return None, None

    def _resolve_module_path(self, source_dir: Path, module: str) -> Optional[Path]:
        """Resolve relative module path."""
        # Handle ./ and ../ prefixes
        if module.startswith("./"):
            module = module[2:]
        elif module.startswith("../"):
            source_dir = source_dir.parent
            module = module[3:]

        # Try common extensions
        for ext in [".py", ".ts", ".tsx", ".js", ".jsx", ""]:
            candidate = source_dir / f"{module.replace('.', '/')}{ext}"
            if str(candidate) in self.index.paths:
                return candidate

            # Try index file
            candidate = source_dir / module.replace(".", "/") / f"index{ext}"
            if str(candidate) in self.index.paths:
                return candidate

        return None

    def _path_matches_module(self, path: str, module: str) -> bool:
        """Check if path matches module name."""
        path_obj = Path(path)
        stem = path_obj.stem

        # Direct match
        if stem == module or stem == module.split(".")[-1]:
            return True

        # Package match (module/index.py)
        if stem == "index" and path_obj.parent.name == module.split(".")[-1]:
            return True

        return False

    def _resolve_inheritance(
        self, rel: Relationship
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve class inheritance to target class."""
        target_name = rel.target_name
        if not target_name:
            return None, None

        # Find class definition
        matches = self.index.find_symbol(target_name)
        for doc_id, node_id in matches:
            doc = self.index.get_by_id(doc_id)
            if doc:
                node = doc.get_node(node_id)
                if node and node.type == NodeType.CLASS:
                    return doc_id, node_id

        return None, None

    def _resolve_link(self, rel: Relationship) -> tuple[Optional[str], Optional[str]]:
        """Resolve document link to target."""
        target_name = rel.target_name or ""

        # Handle anchor links
        if target_name.startswith("#"):
            # Same document anchor
            doc = self.index.get_by_id(rel.source_document_id)
            if doc:
                slug = target_name[1:]
                node = doc.symbols.get(slug)
                if node:
                    return rel.source_document_id, node.id
            return rel.source_document_id, None

        # Handle file links
        source_doc = self.index.get_by_id(rel.source_document_id)
        if source_doc:
            source_dir = Path(source_doc.file_path).parent
            target_path = source_dir / target_name

            # Handle anchors in file links
            anchor = None
            if "#" in target_name:
                target_name, anchor = target_name.split("#", 1)
                target_path = source_dir / target_name

            target_doc = self.index.get_by_path(str(target_path))
            if target_doc:
                if anchor:
                    node = target_doc.symbols.get(anchor)
                    if node:
                        return target_doc.id, node.id
                return target_doc.id, None

        return None, None

    def _resolve_reference(
        self, rel: Relationship
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve generic reference (e.g., LaTeX \\ref)."""
        target_name = rel.target_name
        if not target_name:
            return None, None

        # Search all documents for the label
        for doc_id, doc in self.index.documents.items():
            # Check labels in metadata
            labels = doc.metadata.get("labels", {})
            if target_name in labels:
                return doc_id, labels[target_name]

            # Check symbols
            if target_name in doc.symbols:
                node = doc.symbols[target_name]
                return doc_id, node.id

        return None, None

    def _resolve_foreign_key(
        self, rel: Relationship
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve SQL foreign key to target table."""
        target_name = rel.target_name
        if not target_name:
            return None, None

        # Find table definition
        matches = self.index.find_symbol(target_name)
        for doc_id, node_id in matches:
            doc = self.index.get_by_id(doc_id)
            if doc:
                node = doc.get_node(node_id)
                if node and node.type == NodeType.TABLE:
                    return doc_id, node_id

        return None, None

    def _resolve_citation(
        self, rel: Relationship
    ) -> tuple[Optional[str], Optional[str]]:
        """Resolve citation to bibliography entry."""
        target_name = rel.target_name
        if not target_name:
            return None, None

        # Search for bibliography entries
        for doc_id, doc in self.index.documents.items():
            # Check for BibTeX entries
            bib_entries = doc.metadata.get("bib_entries", {})
            if target_name in bib_entries:
                return doc_id, bib_entries[target_name]

        return None, None

    def get_references_from(self, doc_id: str) -> list[CrossReference]:
        """Get all cross-references from a document."""
        return [xref for xref in self.cross_references if xref.source_document_id == doc_id]

    def get_references_to(self, doc_id: str) -> list[CrossReference]:
        """Get all cross-references to a document."""
        return [xref for xref in self.cross_references if xref.target_document_id == doc_id]

    def get_unresolved(self) -> list[Relationship]:
        """Get relationships that couldn't be resolved."""
        resolved_sources = {
            (xref.source_document_id, xref.source_node_id)
            for xref in self.cross_references
        }

        return [
            rel
            for rel in self.extractor.relationships
            if (rel.source_document_id, rel.source_node_id) not in resolved_sources
        ]

    def build_graph(self) -> dict[str, dict]:
        """Build document dependency graph."""
        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        for doc_id, doc in self.index.documents.items():
            nodes[doc_id] = {
                "id": doc_id,
                "path": doc.file_path,
                "type": doc.file_type,
                "title": doc.title or Path(doc.file_path).stem,
            }

        for xref in self.cross_references:
            edges.append({
                "source": xref.source_document_id,
                "target": xref.target_document_id,
                "type": xref.reference_type,
            })

        return {"nodes": nodes, "edges": edges}

    def to_dict(self) -> dict:
        """Export cross-references as dictionary."""
        return {
            "total": len(self.cross_references),
            "resolved": len(self.cross_references),
            "unresolved": len(self.get_unresolved()),
            "cross_references": [xref.model_dump() for xref in self.cross_references],
            "graph": self.build_graph(),
        }
