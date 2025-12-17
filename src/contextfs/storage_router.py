"""
Unified Storage Router for ContextFS.

Provides a single interface for all memory storage operations,
ensuring SQLite and ChromaDB stay synchronized.

This solves the mismatch where:
- Auto-indexed memories were only in ChromaDB (search worked, recall failed)
- Manual memories were in both (everything worked)

Now all operations go through this router to maintain consistency.

Implements the StorageBackend protocol for type-safe pluggability.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from contextfs.rag import RAGBackend
from contextfs.schemas import Memory, MemoryType, SearchResult
from contextfs.storage_protocol import (
    UNIFIED_CAPABILITIES,
    StorageBackend,
    StorageCapabilities,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StorageRouter(StorageBackend):
    """
    Unified storage router for SQLite and ChromaDB.

    Implements the StorageBackend protocol, ensuring type-safe
    pluggability with other storage implementations.

    Ensures all memory operations keep both backends in sync:
    - SQLite: Persistent storage, FTS, structured queries
    - ChromaDB: Semantic search, vector embeddings

    Provides unified search that queries the appropriate backend.
    """

    # Class-level capabilities descriptor
    capabilities: StorageCapabilities = UNIFIED_CAPABILITIES

    def __init__(
        self,
        db_path: Path,
        rag_backend: RAGBackend,
    ) -> None:
        """
        Initialize storage router.

        Args:
            db_path: Path to SQLite database
            rag_backend: RAGBackend instance for vector storage
        """
        self._db_path = db_path
        self._rag = rag_backend

    # ==================== Write Operations ====================

    def save(self, memory: Memory) -> Memory:
        """
        Save a memory to both SQLite and ChromaDB.

        Args:
            memory: Memory object to save

        Returns:
            Saved Memory object
        """
        # Save to SQLite first (always succeeds)
        self._save_to_sqlite(memory)

        # Save to ChromaDB (may fail if corrupted)
        try:
            self._rag.add_memory(memory)
        except Exception as e:
            logger.warning(f"ChromaDB save failed (memory saved to SQLite): {e}")

        return memory

    def save_batch(self, memories: list[Memory]) -> int:
        """
        Save multiple memories to both SQLite and ChromaDB.

        Much faster than individual saves for auto-indexing.

        Args:
            memories: List of Memory objects to save

        Returns:
            Number of memories successfully saved to SQLite
        """
        if not memories:
            return 0

        # Batch save to SQLite first (always succeeds)
        self._save_batch_to_sqlite(memories)

        # Batch save to ChromaDB (may fail if corrupted)
        try:
            self._rag.add_memories_batch(memories)
        except Exception as e:
            logger.warning(f"ChromaDB batch save failed (memories saved to SQLite): {e}")

        # Return count of memories saved to SQLite (the authoritative store)
        return len(memories)

    def _save_to_sqlite(self, memory: Memory) -> None:
        """Save a single memory to SQLite."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, content, type, tags, summary, namespace_id,
                 source_file, source_repo, source_tool, project,
                 session_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    memory.content,
                    memory.type.value,
                    json.dumps(memory.tags),
                    memory.summary,
                    memory.namespace_id,
                    memory.source_file,
                    memory.source_repo,
                    memory.source_tool,
                    memory.project,
                    memory.session_id,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                    json.dumps(memory.metadata),
                ),
            )

            # Update FTS
            cursor.execute(
                """
                INSERT OR REPLACE INTO memories_fts (id, content, summary, tags)
                VALUES (?, ?, ?, ?)
            """,
                (memory.id, memory.content, memory.summary, " ".join(memory.tags)),
            )

            conn.commit()
        finally:
            conn.close()

    def _save_batch_to_sqlite(self, memories: list[Memory]) -> None:
        """Batch save memories to SQLite (much faster)."""
        if not memories:
            return

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Prepare batch data
            memory_rows = [
                (
                    m.id,
                    m.content,
                    m.type.value,
                    json.dumps(m.tags),
                    m.summary,
                    m.namespace_id,
                    m.source_file,
                    m.source_repo,
                    m.source_tool,
                    m.project,
                    m.session_id,
                    m.created_at.isoformat(),
                    m.updated_at.isoformat(),
                    json.dumps(m.metadata),
                )
                for m in memories
            ]

            fts_rows = [(m.id, m.content, m.summary, " ".join(m.tags)) for m in memories]

            # Batch insert
            cursor.executemany(
                """
                INSERT OR REPLACE INTO memories
                (id, content, type, tags, summary, namespace_id,
                 source_file, source_repo, source_tool, project,
                 session_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                memory_rows,
            )

            cursor.executemany(
                """
                INSERT OR REPLACE INTO memories_fts (id, content, summary, tags)
                VALUES (?, ?, ?, ?)
            """,
                fts_rows,
            )

            conn.commit()
        finally:
            conn.close()

    # ==================== Read Operations ====================

    def recall(self, memory_id: str) -> Memory | None:
        """
        Recall a specific memory by ID.

        Tries SQLite first (faster), falls back to ChromaDB.

        Args:
            memory_id: Memory ID (can be partial, at least 8 chars)

        Returns:
            Memory or None
        """
        # Try SQLite first
        memory = self._recall_from_sqlite(memory_id)
        if memory:
            return memory

        # Fall back to ChromaDB
        return self._recall_from_chromadb(memory_id)

    def _recall_from_sqlite(self, memory_id: str) -> Memory | None:
        """Recall memory from SQLite."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM memories WHERE id LIKE ?", (f"{memory_id}%",))
            row = cursor.fetchone()

            if row:
                return self._row_to_memory(row)
            return None
        finally:
            conn.close()

    def _recall_from_chromadb(self, memory_id: str) -> Memory | None:
        """Recall memory from ChromaDB by ID prefix."""
        self._rag._ensure_initialized()

        try:
            # Get all memories and filter by ID prefix
            # ChromaDB doesn't support LIKE queries, so we need to get by exact ID
            # or search with a broader approach
            results = self._rag._collection.get(
                ids=[memory_id],  # Try exact match first
                include=["documents", "metadatas"],
            )

            if results and results["ids"]:
                return self._chromadb_result_to_memory(results, 0)

            # If exact match failed, try prefix search via metadata
            # This is slower but handles partial IDs
            all_results = self._rag._collection.get(
                include=["documents", "metadatas"],
                limit=10000,  # Get all to filter
            )

            if all_results and all_results["ids"]:
                for i, mid in enumerate(all_results["ids"]):
                    if mid.startswith(memory_id):
                        return self._chromadb_result_to_memory(all_results, i)

            return None
        except Exception as e:
            logger.warning(f"ChromaDB recall failed: {e}")
            return None

    def _chromadb_result_to_memory(self, results: dict, index: int) -> Memory:
        """Convert ChromaDB result to Memory object."""
        memory_id = results["ids"][index]
        document = results["documents"][index] if results.get("documents") else ""
        metadata = results["metadatas"][index] if results.get("metadatas") else {}

        return Memory(
            id=memory_id,
            content=document,
            type=MemoryType(metadata.get("type", "fact")),
            tags=json.loads(metadata.get("tags", "[]")),
            summary=metadata.get("summary") or None,
            namespace_id=metadata.get("namespace_id", "global"),
            created_at=datetime.fromisoformat(
                metadata.get("created_at", datetime.now().isoformat())
            ),
            source_repo=metadata.get("source_repo") or None,
            project=metadata.get("project") or None,
            source_tool=metadata.get("source_tool") or None,
            source_file=metadata.get("source_file") or None,
        )

    def _row_to_memory(self, row: tuple) -> Memory:
        """Convert SQLite row to Memory object."""
        return Memory(
            id=row[0],
            content=row[1],
            type=MemoryType(row[2]),
            tags=json.loads(row[3]) if row[3] else [],
            summary=row[4],
            namespace_id=row[5],
            source_file=row[6],
            source_repo=row[7],
            source_tool=row[8],
            project=row[9],
            session_id=row[10],
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now(),
            updated_at=datetime.fromisoformat(row[12]) if row[12] else datetime.now(),
            metadata=json.loads(row[13]) if row[13] else {},
        )

    # ==================== Search Operations ====================

    def search(
        self,
        query: str,
        limit: int = 10,
        type: MemoryType | None = None,
        tags: list[str] | None = None,
        namespace_id: str | None = None,
        source_tool: str | None = None,
        source_repo: str | None = None,
        project: str | None = None,
        cross_repo: bool = False,
        min_score: float = 0.3,
    ) -> list[SearchResult]:
        """
        Search memories using semantic search (ChromaDB).

        Args:
            query: Search query
            limit: Maximum results
            type: Filter by type
            tags: Filter by tags
            namespace_id: Filter by namespace
            source_tool: Filter by source tool
            source_repo: Filter by source repository
            project: Filter by project
            cross_repo: Search across all namespaces
            min_score: Minimum similarity score

        Returns:
            List of SearchResult objects
        """
        self._rag._ensure_initialized()

        # Generate query embedding
        query_embedding = self._rag._get_embedding(query)

        # Build where filter for ChromaDB
        where = self._build_where_filter(
            type=type,
            namespace_id=namespace_id if not cross_repo else None,
            source_tool=source_tool,
            source_repo=source_repo,
            project=project,
        )

        try:
            results = self._rag._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit * 2,  # Get extra for filtering
                where=where if where else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}")
            return []

        return self._process_search_results(results, limit, tags, min_score)

    def _build_where_filter(
        self,
        type: MemoryType | None = None,
        namespace_id: str | None = None,
        source_tool: str | None = None,
        source_repo: str | None = None,
        project: str | None = None,
    ) -> dict | None:
        """Build ChromaDB where filter from parameters."""
        conditions = []

        if namespace_id:
            conditions.append({"namespace_id": namespace_id})
        if type:
            conditions.append({"type": type.value})
        if source_tool:
            conditions.append({"source_tool": source_tool})
        if source_repo:
            conditions.append({"source_repo": source_repo})
        if project:
            conditions.append({"project": project})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _process_search_results(
        self,
        results: dict,
        limit: int,
        tags: list[str] | None,
        min_score: float,
    ) -> list[SearchResult]:
        """Process ChromaDB results into SearchResult objects."""
        search_results = []

        if not results or not results.get("ids") or not results["ids"][0]:
            return search_results

        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i, memory_id in enumerate(ids):
            # Convert distance to similarity score
            distance = distances[i] if i < len(distances) else 1.0
            score = 1.0 - (distance / 2.0)

            if score < min_score:
                continue

            metadata = metadatas[i] if i < len(metadatas) else {}

            # Filter by tags if specified
            if tags:
                memory_tags = json.loads(metadata.get("tags", "[]"))
                if not any(t in memory_tags for t in tags):
                    continue

            memory = Memory(
                id=memory_id,
                content=documents[i] if i < len(documents) else "",
                type=MemoryType(metadata.get("type", "fact")),
                tags=json.loads(metadata.get("tags", "[]")),
                summary=metadata.get("summary") or None,
                namespace_id=metadata.get("namespace_id", "global"),
                created_at=datetime.fromisoformat(
                    metadata.get("created_at", datetime.now().isoformat())
                ),
                source_repo=metadata.get("source_repo") or None,
                project=metadata.get("project") or None,
                source_tool=metadata.get("source_tool") or None,
                source_file=metadata.get("source_file") or None,
            )

            search_results.append(SearchResult(memory=memory, score=score))

            if len(search_results) >= limit:
                break

        return search_results

    # ==================== Delete Operations ====================

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory from both SQLite and ChromaDB.

        Args:
            memory_id: Memory ID (can be partial)

        Returns:
            True if deleted, False if not found
        """
        deleted_sqlite = self._delete_from_sqlite(memory_id)
        deleted_chromadb = self._delete_from_chromadb(memory_id)

        return deleted_sqlite or deleted_chromadb

    def _delete_from_sqlite(self, memory_id: str) -> bool:
        """Delete memory from SQLite."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Find exact ID first
            cursor.execute("SELECT id FROM memories WHERE id LIKE ?", (f"{memory_id}%",))
            row = cursor.fetchone()

            if not row:
                return False

            full_id = row[0]

            cursor.execute("DELETE FROM memories WHERE id = ?", (full_id,))
            cursor.execute("DELETE FROM memories_fts WHERE id = ?", (full_id,))
            conn.commit()

            return cursor.rowcount > 0
        finally:
            conn.close()

    def _delete_from_chromadb(self, memory_id: str) -> bool:
        """Delete memory from ChromaDB."""
        self._rag._ensure_initialized()

        try:
            # Try exact match first
            self._rag._collection.delete(ids=[memory_id])
            return True
        except Exception:
            # Try prefix match
            try:
                all_results = self._rag._collection.get(include=[])
                if all_results and all_results["ids"]:
                    for mid in all_results["ids"]:
                        if mid.startswith(memory_id):
                            self._rag._collection.delete(ids=[mid])
                            return True
            except Exception:
                pass
            return False

    def delete_by_namespace(self, namespace_id: str) -> int:
        """
        Delete all memories in a namespace from both backends.

        Args:
            namespace_id: Namespace to clear

        Returns:
            Number of memories deleted
        """
        # Delete from SQLite
        sqlite_deleted = self._delete_namespace_from_sqlite(namespace_id)

        # Delete from ChromaDB
        chromadb_deleted = self._rag.delete_by_namespace(namespace_id)

        return max(sqlite_deleted, chromadb_deleted)

    def _delete_namespace_from_sqlite(self, namespace_id: str) -> int:
        """Delete all memories in namespace from SQLite."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            # Get IDs to delete from FTS too
            cursor.execute("SELECT id FROM memories WHERE namespace_id = ?", (namespace_id,))
            ids = [row[0] for row in cursor.fetchall()]

            if ids:
                placeholders = ",".join("?" * len(ids))
                cursor.execute(f"DELETE FROM memories_fts WHERE id IN ({placeholders})", ids)
                cursor.execute("DELETE FROM memories WHERE namespace_id = ?", (namespace_id,))
                conn.commit()

            return len(ids)
        finally:
            conn.close()

    # ==================== Update Operations ====================

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        type: MemoryType | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
        project: str | None = None,
    ) -> Memory | None:
        """
        Update a memory in both SQLite and ChromaDB.

        Args:
            memory_id: Memory ID (can be partial)
            content: New content (optional)
            type: New type (optional)
            tags: New tags (optional)
            summary: New summary (optional)
            project: New project (optional)

        Returns:
            Updated Memory or None if not found
        """
        # Get existing memory
        memory = self.recall(memory_id)
        if not memory:
            return None

        # Apply updates
        if content is not None:
            memory.content = content
        if type is not None:
            memory.type = type
        if tags is not None:
            memory.tags = tags
        if summary is not None:
            memory.summary = summary
        if project is not None:
            memory.project = project

        memory.updated_at = datetime.now()

        # Delete and re-save (simpler than partial updates)
        self.delete(memory.id)
        self.save(memory)

        return memory

    # ==================== List Operations ====================

    def list_recent(
        self,
        limit: int = 10,
        type: MemoryType | None = None,
        namespace_id: str | None = None,
        source_tool: str | None = None,
        project: str | None = None,
    ) -> list[Memory]:
        """
        List recent memories from SQLite.

        Args:
            limit: Maximum results
            type: Filter by type
            namespace_id: Filter by namespace
            source_tool: Filter by source tool
            project: Filter by project

        Returns:
            List of Memory objects
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            sql = "SELECT * FROM memories WHERE 1=1"
            params: list = []

            if namespace_id:
                sql += " AND namespace_id = ?"
                params.append(namespace_id)
            if type:
                sql += " AND type = ?"
                params.append(type.value)
            if source_tool:
                sql += " AND source_tool = ?"
                params.append(source_tool)
            if project:
                sql += " AND project = ?"
                params.append(project)

            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            return [self._row_to_memory(row) for row in rows]
        finally:
            conn.close()

    # ==================== Stats ====================

    def get_stats(self) -> dict:
        """Get storage statistics from both backends."""
        sqlite_count = self._get_sqlite_count()
        chromadb_stats = self._rag.get_stats()

        return {
            "sqlite_memories": sqlite_count,
            "chromadb_memories": chromadb_stats.get("total_memories", 0),
            "in_sync": sqlite_count == chromadb_stats.get("total_memories", 0),
            "embedding_model": chromadb_stats.get("embedding_model"),
        }

    def _get_sqlite_count(self) -> int:
        """Get total memory count from SQLite."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM memories")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def rebuild_chromadb_from_sqlite(
        self,
        on_progress: callable = None,
        batch_size: int = 100,
    ) -> dict:
        """
        Rebuild ChromaDB from SQLite data.

        Use this after ChromaDB corruption to restore search capability
        without needing to re-index from source files.

        Args:
            on_progress: Callback for progress updates (current, total)
            batch_size: Number of memories to process per batch

        Returns:
            Statistics dict with count of memories rebuilt
        """
        # Reset ChromaDB first
        if not self._rag.reset_database():
            return {"success": False, "error": "Failed to reset ChromaDB"}

        # Get all memories from SQLite
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]

            if total == 0:
                return {"success": True, "rebuilt": 0, "total": 0}

            cursor.execute("SELECT * FROM memories ORDER BY created_at")
            rows = cursor.fetchall()

            rebuilt = 0
            errors = 0

            # Process in batches for efficiency
            for i in range(0, len(rows), batch_size):
                batch_rows = rows[i : i + batch_size]
                batch_memories = [self._row_to_memory(row) for row in batch_rows]

                try:
                    self._rag.add_memories_batch(batch_memories)
                    rebuilt += len(batch_memories)
                except Exception as e:
                    logger.warning(f"Failed to add batch to ChromaDB: {e}")
                    # Try individual adds as fallback
                    for memory in batch_memories:
                        try:
                            self._rag.add_memory(memory)
                            rebuilt += 1
                        except Exception:
                            errors += 1

                if on_progress:
                    on_progress(rebuilt, total)

            return {
                "success": True,
                "rebuilt": rebuilt,
                "total": total,
                "errors": errors,
            }

        finally:
            conn.close()
