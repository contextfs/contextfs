"""
ContextFS Expander Algorithm
============================

A type-theoretic approach to expanding compressed memory representations
into full context for AI consumption. Implements the "Git for AI conversations"
paradigm where context diffs are expanded into complete, type-safe contexts.

Core Concepts:
- MemoryAtom: Minimal unit of typed information
- MemoryMolecule: Composed structures with type constraints  
- ExpansionFunctor: Category-theoretic expansion preserving structure
- ContextLattice: Partial ordering of context relevance
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    TypeVar, Generic, Callable, Iterator, Optional, 
    Protocol, runtime_checkable, Any, Mapping
)
from enum import Enum, auto
from collections import defaultdict
import hashlib
import json
from datetime import datetime
from functools import cached_property


# =============================================================================
# Type Universe - The foundational type system
# =============================================================================

class Kind(Enum):
    """Kinds classify types (types of types)"""
    STAR = auto()          # * - concrete types
    ARROW = auto()         # * -> * - type constructors
    CONSTRAINT = auto()    # Constraint kinds
    CONTEXT = auto()       # Context-specific kinds


@dataclass(frozen=True)
class TypeSignature:
    """
    Type signature for memory atoms.
    Implements a simple dependent type system for context.
    """
    name: str
    kind: Kind
    parameters: tuple[TypeSignature, ...] = ()
    constraints: tuple[str, ...] = ()
    
    def __repr__(self) -> str:
        if self.parameters:
            params = ", ".join(str(p) for p in self.parameters)
            return f"{self.name}[{params}]"
        return self.name
    
    def unify(self, other: TypeSignature) -> Optional[TypeSignature]:
        """Attempt to unify two type signatures (simplified unification)"""
        if self.name == other.name and self.kind == other.kind:
            if len(self.parameters) == len(other.parameters):
                unified_params = []
                for p1, p2 in zip(self.parameters, other.parameters):
                    unified = p1.unify(p2)
                    if unified is None:
                        return None
                    unified_params.append(unified)
                return TypeSignature(
                    self.name, 
                    self.kind, 
                    tuple(unified_params),
                    tuple(set(self.constraints) | set(other.constraints))
                )
        # Check for type variable (wildcard) unification
        if self.name.startswith('τ') or other.name.startswith('τ'):
            return self if not self.name.startswith('τ') else other
        return None


# Primitive type signatures
T_STRING = TypeSignature("String", Kind.STAR)
T_INT = TypeSignature("Int", Kind.STAR)
T_FLOAT = TypeSignature("Float", Kind.STAR)
T_BOOL = TypeSignature("Bool", Kind.STAR)
T_TIMESTAMP = TypeSignature("Timestamp", Kind.STAR)
T_ANY = TypeSignature("τ_any", Kind.STAR)  # Type variable


def T_LIST(inner: TypeSignature) -> TypeSignature:
    return TypeSignature("List", Kind.ARROW, (inner,))

def T_DICT(key: TypeSignature, value: TypeSignature) -> TypeSignature:
    return TypeSignature("Dict", Kind.ARROW, (key, value))

def T_CONTEXT(inner: TypeSignature) -> TypeSignature:
    return TypeSignature("Context", Kind.CONTEXT, (inner,))


# =============================================================================
# Memory Atoms - The fundamental units
# =============================================================================

@dataclass(frozen=True)
class MemoryAtom:
    """
    Minimal unit of typed information in the context system.
    Immutable and content-addressable.
    """
    content: str
    type_sig: TypeSignature
    timestamp: datetime
    source_hash: str
    relevance_score: float = 1.0
    
    @cached_property
    def content_hash(self) -> str:
        """Content-addressable hash for deduplication"""
        hasher = hashlib.sha256()
        hasher.update(self.content.encode('utf-8'))
        hasher.update(str(self.type_sig).encode('utf-8'))
        return hasher.hexdigest()[:16]
    
    def __hash__(self) -> int:
        return hash(self.content_hash)
    
    def typed_as(self, new_type: TypeSignature) -> Optional[MemoryAtom]:
        """Attempt to retype this atom (type coercion)"""
        unified = self.type_sig.unify(new_type)
        if unified:
            return MemoryAtom(
                self.content, unified, self.timestamp,
                self.source_hash, self.relevance_score
            )
        return None


# =============================================================================
# Memory Molecules - Composed structures
# =============================================================================

@dataclass
class MemoryMolecule:
    """
    Composed structure of memory atoms with relational constraints.
    Represents a coherent unit of context.
    """
    atoms: list[MemoryAtom]
    relations: dict[str, list[tuple[int, int]]]  # relation_name -> [(atom_idx, atom_idx)]
    molecule_type: TypeSignature
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @property
    def complexity(self) -> int:
        """Structural complexity measure"""
        return len(self.atoms) + sum(len(r) for r in self.relations.values())
    
    def project(self, type_filter: TypeSignature) -> MemoryMolecule:
        """Project molecule onto a type subspace"""
        filtered_atoms = []
        idx_map = {}
        
        for i, atom in enumerate(self.atoms):
            if atom.type_sig.unify(type_filter):
                idx_map[i] = len(filtered_atoms)
                filtered_atoms.append(atom)
        
        filtered_relations = defaultdict(list)
        for rel_name, pairs in self.relations.items():
            for i, j in pairs:
                if i in idx_map and j in idx_map:
                    filtered_relations[rel_name].append((idx_map[i], idx_map[j]))
        
        return MemoryMolecule(
            filtered_atoms, 
            dict(filtered_relations),
            T_CONTEXT(type_filter),
            self.metadata
        )


# =============================================================================
# Expansion Strategies - The core algorithms
# =============================================================================

@runtime_checkable
class ExpansionStrategy(Protocol):
    """Protocol for expansion strategies"""
    def expand(self, compressed: CompressedContext) -> ExpandedContext: ...
    def estimate_cost(self, compressed: CompressedContext) -> int: ...


@dataclass
class CompressedContext:
    """
    A compressed representation of context.
    Analogous to a Git commit/diff.
    """
    base_hash: Optional[str]  # Parent context hash (None for root)
    delta_atoms: list[MemoryAtom]
    delta_molecules: list[MemoryMolecule]
    removed_hashes: set[str]
    compression_metadata: dict[str, Any]
    
    @property 
    def is_root(self) -> bool:
        return self.base_hash is None
    
    @property
    def delta_size(self) -> int:
        return len(self.delta_atoms) + sum(m.complexity for m in self.delta_molecules)


@dataclass  
class ExpandedContext:
    """
    Fully expanded context ready for AI consumption.
    """
    atoms: list[MemoryAtom]
    molecules: list[MemoryMolecule]
    expansion_path: list[str]  # Chain of hashes from root
    total_tokens_estimate: int
    type_summary: dict[str, int]  # type_name -> count
    
    def to_prompt_context(self, max_tokens: int = 4000) -> str:
        """Serialize to prompt-ready format with token budget"""
        lines = []
        current_tokens = 0
        
        # Sort by relevance
        sorted_atoms = sorted(self.atoms, key=lambda a: -a.relevance_score)
        
        for atom in sorted_atoms:
            atom_str = f"[{atom.type_sig}] {atom.content}"
            atom_tokens = len(atom_str.split()) * 1.3  # Rough estimate
            
            if current_tokens + atom_tokens > max_tokens:
                break
                
            lines.append(atom_str)
            current_tokens += atom_tokens
        
        return "\n".join(lines)


# =============================================================================
# The Expander Functor - Category-theoretic expansion
# =============================================================================

class ExpanderFunctor:
    """
    The main expander implementing a functor from CompressedContext to ExpandedContext.
    
    This is a functor in the category-theoretic sense:
    - Objects: Context states (compressed and expanded)
    - Morphisms: Context transformations (diffs)
    - Functor: Maps compressed transformations to expanded transformations
    
    The functor laws ensure:
    1. Identity: expand(id) = id (expanding nothing changes nothing)
    2. Composition: expand(f ∘ g) = expand(f) ∘ expand(g)
    """
    
    def __init__(self, context_store: ContextStore):
        self.store = context_store
        self._expansion_cache: dict[str, ExpandedContext] = {}
    
    def expand(self, compressed: CompressedContext) -> ExpandedContext:
        """
        Main expansion algorithm.
        
        Algorithm:
        1. If root context, expand directly
        2. Otherwise, recursively expand base and apply delta
        3. Apply type-directed optimization
        4. Cache result for memoization
        """
        # Check cache first
        cache_key = self._compute_cache_key(compressed)
        if cache_key in self._expansion_cache:
            return self._expansion_cache[cache_key]
        
        if compressed.is_root:
            result = self._expand_root(compressed)
        else:
            result = self._expand_delta(compressed)
        
        # Apply type-directed compaction
        result = self._type_compact(result)
        
        self._expansion_cache[cache_key] = result
        return result
    
    def _expand_root(self, compressed: CompressedContext) -> ExpandedContext:
        """Expand a root context (no base)"""
        type_summary = defaultdict(int)
        
        for atom in compressed.delta_atoms:
            type_summary[str(atom.type_sig)] += 1
        
        return ExpandedContext(
            atoms=list(compressed.delta_atoms),
            molecules=list(compressed.delta_molecules),
            expansion_path=[self._compute_cache_key(compressed)],
            total_tokens_estimate=self._estimate_tokens(compressed.delta_atoms),
            type_summary=dict(type_summary)
        )
    
    def _expand_delta(self, compressed: CompressedContext) -> ExpandedContext:
        """Expand a delta context by first expanding the base"""
        # Retrieve and expand base
        base_compressed = self.store.get(compressed.base_hash)
        if base_compressed is None:
            raise ValueError(f"Base context not found: {compressed.base_hash}")
        
        base_expanded = self.expand(base_compressed)
        
        # Apply delta: remove atoms, add new atoms
        atom_set = {a.content_hash: a for a in base_expanded.atoms}
        
        for hash_to_remove in compressed.removed_hashes:
            atom_set.pop(hash_to_remove, None)
        
        for new_atom in compressed.delta_atoms:
            atom_set[new_atom.content_hash] = new_atom
        
        # Merge molecules (simplified - could use more sophisticated merging)
        molecules = list(base_expanded.molecules) + list(compressed.delta_molecules)
        
        # Build type summary
        type_summary = defaultdict(int)
        for atom in atom_set.values():
            type_summary[str(atom.type_sig)] += 1
        
        return ExpandedContext(
            atoms=list(atom_set.values()),
            molecules=molecules,
            expansion_path=base_expanded.expansion_path + [self._compute_cache_key(compressed)],
            total_tokens_estimate=self._estimate_tokens(list(atom_set.values())),
            type_summary=dict(type_summary)
        )
    
    def _type_compact(self, context: ExpandedContext) -> ExpandedContext:
        """
        Type-directed compaction: merge atoms with compatible types.
        Implements a form of type-safe garbage collection.
        """
        # Group atoms by type
        type_groups: dict[str, list[MemoryAtom]] = defaultdict(list)
        for atom in context.atoms:
            type_groups[str(atom.type_sig)].append(atom)
        
        # Within each type group, deduplicate and merge
        compacted_atoms = []
        for type_name, atoms in type_groups.items():
            # Keep highest relevance version of each unique content
            seen_content: dict[str, MemoryAtom] = {}
            for atom in atoms:
                content_key = atom.content[:100]  # Prefix key
                if content_key not in seen_content:
                    seen_content[content_key] = atom
                elif atom.relevance_score > seen_content[content_key].relevance_score:
                    seen_content[content_key] = atom
            
            compacted_atoms.extend(seen_content.values())
        
        return ExpandedContext(
            atoms=compacted_atoms,
            molecules=context.molecules,
            expansion_path=context.expansion_path,
            total_tokens_estimate=self._estimate_tokens(compacted_atoms),
            type_summary=context.type_summary
        )
    
    def _compute_cache_key(self, compressed: CompressedContext) -> str:
        """Compute a cache key for a compressed context"""
        hasher = hashlib.sha256()
        hasher.update((compressed.base_hash or "ROOT").encode())
        for atom in compressed.delta_atoms:
            hasher.update(atom.content_hash.encode())
        return hasher.hexdigest()[:16]
    
    def _estimate_tokens(self, atoms: list[MemoryAtom]) -> int:
        """Estimate token count for a list of atoms"""
        return sum(len(a.content.split()) for a in atoms) * 13 // 10


# =============================================================================
# Context Store - The persistence layer interface
# =============================================================================

class ContextStore(ABC):
    """Abstract interface for context storage (implement with DuckDB, SQLite, etc.)"""
    
    @abstractmethod
    def get(self, hash_key: str) -> Optional[CompressedContext]: ...
    
    @abstractmethod
    def put(self, compressed: CompressedContext) -> str: ...
    
    @abstractmethod
    def get_lineage(self, hash_key: str) -> list[str]: ...


class InMemoryContextStore(ContextStore):
    """Simple in-memory implementation for testing"""
    
    def __init__(self):
        self._store: dict[str, CompressedContext] = {}
    
    def get(self, hash_key: str) -> Optional[CompressedContext]:
        return self._store.get(hash_key)
    
    def put(self, compressed: CompressedContext) -> str:
        hasher = hashlib.sha256()
        hasher.update((compressed.base_hash or "ROOT").encode())
        for atom in compressed.delta_atoms:
            hasher.update(atom.content_hash.encode())
        key = hasher.hexdigest()[:16]
        self._store[key] = compressed
        return key
    
    def get_lineage(self, hash_key: str) -> list[str]:
        lineage = []
        current = hash_key
        while current:
            lineage.append(current)
            ctx = self._store.get(current)
            if ctx is None:
                break
            current = ctx.base_hash
        return list(reversed(lineage))


# =============================================================================
# Relevance Lattice - Partial ordering for context prioritization
# =============================================================================

@dataclass
class RelevanceLattice:
    """
    Implements a lattice structure for context relevance.
    
    The lattice allows computing:
    - meet (greatest lower bound): most restrictive common context
    - join (least upper bound): most permissive common context
    """
    
    atoms: list[MemoryAtom]
    _adjacency: dict[str, set[str]] = field(default_factory=dict)
    
    def add_relevance_edge(self, from_hash: str, to_hash: str):
        """from_hash is more relevant than to_hash"""
        if from_hash not in self._adjacency:
            self._adjacency[from_hash] = set()
        self._adjacency[from_hash].add(to_hash)
    
    def meet(self, hashes: set[str]) -> set[str]:
        """Greatest lower bound - atoms relevant to ALL given contexts"""
        if not hashes:
            return set()
        
        result = None
        for h in hashes:
            reachable = self._reachable_from(h)
            reachable.add(h)
            if result is None:
                result = reachable
            else:
                result &= reachable
        
        return result or set()
    
    def join(self, hashes: set[str]) -> set[str]:
        """Least upper bound - atoms relevant to ANY given context"""
        result = set()
        for h in hashes:
            reachable = self._reachable_from(h)
            reachable.add(h)
            result |= reachable
        return result
    
    def _reachable_from(self, start: str) -> set[str]:
        """BFS to find all reachable nodes"""
        visited = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self._adjacency.get(current, []))
        visited.discard(start)
        return visited


# =============================================================================
# Incremental Expander - For streaming/real-time expansion
# =============================================================================

class IncrementalExpander:
    """
    Incremental expansion for real-time context updates.
    
    Instead of full expansion, this maintains a running expanded context
    and applies incremental updates. More efficient for streaming scenarios.
    """
    
    def __init__(self, store: ContextStore):
        self.store = store
        self.current_expanded: Optional[ExpandedContext] = None
        self._atom_index: dict[str, MemoryAtom] = {}
    
    def initialize(self, compressed: CompressedContext):
        """Initialize with a base context"""
        functor = ExpanderFunctor(self.store)
        self.current_expanded = functor.expand(compressed)
        self._rebuild_index()
    
    def apply_delta(self, delta: CompressedContext) -> ExpandedContext:
        """Apply an incremental delta to the current context"""
        if self.current_expanded is None:
            raise ValueError("Must initialize before applying deltas")
        
        # Remove atoms
        for hash_to_remove in delta.removed_hashes:
            self._atom_index.pop(hash_to_remove, None)
        
        # Add new atoms
        for atom in delta.delta_atoms:
            self._atom_index[atom.content_hash] = atom
        
        # Rebuild expanded context
        atoms = list(self._atom_index.values())
        molecules = self.current_expanded.molecules + list(delta.delta_molecules)
        
        type_summary = defaultdict(int)
        for atom in atoms:
            type_summary[str(atom.type_sig)] += 1
        
        self.current_expanded = ExpandedContext(
            atoms=atoms,
            molecules=molecules,
            expansion_path=self.current_expanded.expansion_path + ["incremental"],
            total_tokens_estimate=sum(len(a.content.split()) for a in atoms) * 13 // 10,
            type_summary=dict(type_summary)
        )
        
        return self.current_expanded
    
    def _rebuild_index(self):
        """Rebuild the atom index from current expanded context"""
        self._atom_index = {a.content_hash: a for a in self.current_expanded.atoms}


# =============================================================================
# Query Interface - Type-safe context queries
# =============================================================================

@dataclass
class ContextQuery:
    """
    Type-safe query for context retrieval.
    Supports filtering by type, relevance, and temporal constraints.
    """
    type_filter: Optional[TypeSignature] = None
    min_relevance: float = 0.0
    max_age_seconds: Optional[int] = None
    limit: Optional[int] = None
    
    def matches(self, atom: MemoryAtom, now: datetime) -> bool:
        """Check if an atom matches this query"""
        if self.type_filter and not atom.type_sig.unify(self.type_filter):
            return False
        
        if atom.relevance_score < self.min_relevance:
            return False
        
        if self.max_age_seconds:
            age = (now - atom.timestamp).total_seconds()
            if age > self.max_age_seconds:
                return False
        
        return True
    
    def apply(self, context: ExpandedContext) -> list[MemoryAtom]:
        """Apply query to an expanded context"""
        now = datetime.now()
        results = [a for a in context.atoms if self.matches(a, now)]
        results.sort(key=lambda a: -a.relevance_score)
        
        if self.limit:
            results = results[:self.limit]
        
        return results


# =============================================================================
# Example Usage
# =============================================================================

def demo():
    """Demonstrate the expander algorithm"""
    
    # Create a context store
    store = InMemoryContextStore()
    
    # Create some memory atoms
    now = datetime.now()
    
    atoms = [
        MemoryAtom(
            "User prefers Python for local development",
            T_STRING,
            now,
            "conv_001",
            0.9
        ),
        MemoryAtom(
            "ContextFS uses type-theoretic principles",
            T_STRING,
            now,
            "conv_001",
            0.95
        ),
        MemoryAtom(
            "Performance analysis shows AI inference dominates latency",
            T_STRING,
            now,
            "conv_002",
            0.85
        ),
    ]
    
    # Create a root compressed context
    root_context = CompressedContext(
        base_hash=None,
        delta_atoms=atoms[:2],
        delta_molecules=[],
        removed_hashes=set(),
        compression_metadata={"source": "initial"}
    )
    
    root_hash = store.put(root_context)
    print(f"Stored root context: {root_hash}")
    
    # Create a delta context
    delta_context = CompressedContext(
        base_hash=root_hash,
        delta_atoms=[atoms[2]],
        delta_molecules=[],
        removed_hashes=set(),
        compression_metadata={"source": "update_001"}
    )
    
    delta_hash = store.put(delta_context)
    print(f"Stored delta context: {delta_hash}")
    
    # Expand the delta context
    expander = ExpanderFunctor(store)
    expanded = expander.expand(delta_context)
    
    print(f"\nExpanded context:")
    print(f"  Atoms: {len(expanded.atoms)}")
    print(f"  Expansion path: {expanded.expansion_path}")
    print(f"  Estimated tokens: {expanded.total_tokens_estimate}")
    print(f"  Type summary: {expanded.type_summary}")
    
    print(f"\nPrompt context:\n{expanded.to_prompt_context()}")
    
    # Query the context
    query = ContextQuery(min_relevance=0.9)
    results = query.apply(expanded)
    print(f"\nHigh-relevance atoms ({len(results)}):")
    for atom in results:
        print(f"  [{atom.relevance_score}] {atom.content[:50]}...")


if __name__ == "__main__":
    demo()
