"""
Storage Backend Protocol for ContextFS.

Defines type-safe interfaces for pluggable storage backends.
Enables modular architecture where SQLite, ChromaDB, Postgres,
or other backends can be swapped or combined.

Usage:
    class MyCustomBackend:
        def save(self, memory: Memory) -> Memory: ...
        def recall(self, memory_id: str) -> Memory | None: ...
        # ... implement all protocol methods

    # Type checker validates implementation
    backend: StorageBackend = MyCustomBackend()
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from contextfs.schemas import Memory, MemoryType, SearchResult


@runtime_checkable
class StorageBackend(Protocol):
    """
    Protocol for storage backends.

    Any class implementing these methods can be used as a storage backend.
    Use @runtime_checkable to allow isinstance() checks.
    """

    @abstractmethod
    def save(self, memory: Memory) -> Memory:
        """
        Save a memory to storage.

        Args:
            memory: Memory object to save

        Returns:
            Saved Memory object (may have updated fields)
        """
        ...

    @abstractmethod
    def save_batch(self, memories: list[Memory]) -> int:
        """
        Save multiple memories in batch.

        Args:
            memories: List of Memory objects to save

        Returns:
            Number of memories successfully saved
        """
        ...

    @abstractmethod
    def recall(self, memory_id: str) -> Memory | None:
        """
        Recall a specific memory by ID.

        Args:
            memory_id: Memory ID (can be partial, at least 8 chars)

        Returns:
            Memory if found, None otherwise
        """
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        type: MemoryType | None = None,
        tags: list[str] | None = None,
        namespace_id: str | None = None,
        project: str | None = None,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        """
        Search memories.

        Args:
            query: Search query
            limit: Maximum results
            type: Filter by memory type
            tags: Filter by tags
            namespace_id: Filter by namespace
            project: Filter by project
            min_score: Minimum similarity score

        Returns:
            List of SearchResult objects
        """
        ...

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: Memory ID (can be partial)

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    def delete_by_namespace(self, namespace_id: str) -> int:
        """
        Delete all memories in a namespace.

        Args:
            namespace_id: Namespace to clear

        Returns:
            Number of memories deleted
        """
        ...


@runtime_checkable
class SearchableBackend(Protocol):
    """
    Protocol for backends that support semantic search.

    Extends basic storage with vector similarity search.
    """

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        type: MemoryType | None = None,
        namespace_id: str | None = None,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        """Semantic search for similar memories."""
        ...

    @abstractmethod
    def get_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        ...


@runtime_checkable
class PersistentBackend(Protocol):
    """
    Protocol for backends with SQL-like persistent storage.

    Supports structured queries and transactions.
    """

    @abstractmethod
    def save(self, memory: Memory) -> Memory:
        """Save memory to persistent storage."""
        ...

    @abstractmethod
    def recall(self, memory_id: str) -> Memory | None:
        """Recall by exact or partial ID."""
        ...

    @abstractmethod
    def list_recent(
        self,
        limit: int = 10,
        type: MemoryType | None = None,
        namespace_id: str | None = None,
    ) -> list[Memory]:
        """List recent memories with filters."""
        ...

    @abstractmethod
    def update(
        self,
        memory_id: str,
        content: str | None = None,
        type: MemoryType | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
    ) -> Memory | None:
        """Update an existing memory."""
        ...


@runtime_checkable
class SyncableBackend(Protocol):
    """
    Protocol for backends that support synchronization.

    Used for multi-device sync, backup, and replication.
    """

    @abstractmethod
    def get_changes_since(self, timestamp: str) -> list[Memory]:
        """Get all changes since a timestamp."""
        ...

    @abstractmethod
    def apply_changes(self, memories: list[Memory]) -> int:
        """Apply changes from another source."""
        ...

    @abstractmethod
    def get_sync_status(self) -> dict:
        """Get synchronization status."""
        ...


class StorageCapabilities:
    """
    Describes what a storage backend supports.

    Used for feature detection at runtime.
    """

    def __init__(
        self,
        semantic_search: bool = False,
        full_text_search: bool = False,
        persistent: bool = False,
        syncable: bool = False,
        batch_operations: bool = False,
        transactions: bool = False,
    ):
        self.semantic_search = semantic_search
        self.full_text_search = full_text_search
        self.persistent = persistent
        self.syncable = syncable
        self.batch_operations = batch_operations
        self.transactions = transactions

    def __repr__(self) -> str:
        caps = []
        if self.semantic_search:
            caps.append("semantic_search")
        if self.full_text_search:
            caps.append("fts")
        if self.persistent:
            caps.append("persistent")
        if self.syncable:
            caps.append("syncable")
        if self.batch_operations:
            caps.append("batch")
        if self.transactions:
            caps.append("transactions")
        return f"StorageCapabilities({', '.join(caps)})"


# Common capability configurations
SQLITE_CAPABILITIES = StorageCapabilities(
    full_text_search=True,
    persistent=True,
    batch_operations=True,
    transactions=True,
)

CHROMADB_CAPABILITIES = StorageCapabilities(
    semantic_search=True,
    batch_operations=True,
)

UNIFIED_CAPABILITIES = StorageCapabilities(
    semantic_search=True,
    full_text_search=True,
    persistent=True,
    batch_operations=True,
    transactions=True,
)
