"""
ContextFS Expansion Protocol
============================

Protocol layer for the expander algorithm, supporting:
- Async streaming expansion for real-time AI interactions
- Wire protocol for distributed context sharing
- Type-safe serialization/deserialization
- Backpressure handling for large context trees

This implements the "Git for AI" protocol layer.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field, asdict
from typing import AsyncIterator, Optional, Protocol, TypeVar, Generic
from enum import Enum, auto
import json
import struct
from datetime import datetime
import hashlib

from contextfs_expander import (
    MemoryAtom, MemoryMolecule, CompressedContext, ExpandedContext,
    TypeSignature, Kind, ContextStore, ExpanderFunctor,
    T_STRING, T_ANY, T_CONTEXT
)


# =============================================================================
# Protocol Messages
# =============================================================================

class MessageType(Enum):
    """Wire protocol message types"""
    # Client -> Server
    EXPAND_REQUEST = 0x01
    STREAM_REQUEST = 0x02
    QUERY_REQUEST = 0x03
    PUSH_CONTEXT = 0x04
    
    # Server -> Client
    EXPAND_RESPONSE = 0x81
    STREAM_CHUNK = 0x82
    STREAM_END = 0x83
    QUERY_RESPONSE = 0x84
    ACK = 0x85
    ERROR = 0xFF


@dataclass
class ProtocolMessage:
    """Base protocol message"""
    msg_type: MessageType
    sequence_id: int
    payload: dict
    
    def serialize(self) -> bytes:
        """Serialize to wire format"""
        payload_json = json.dumps(self.payload, default=str).encode('utf-8')
        header = struct.pack(
            '>BIH',  # type (1), sequence (4), payload_len (2)
            self.msg_type.value,
            self.sequence_id,
            len(payload_json)
        )
        return header + payload_json
    
    @classmethod
    def deserialize(cls, data: bytes) -> ProtocolMessage:
        """Deserialize from wire format"""
        msg_type, seq_id, payload_len = struct.unpack('>BIH', data[:7])
        payload = json.loads(data[7:7+payload_len].decode('utf-8'))
        return cls(MessageType(msg_type), seq_id, payload)


# =============================================================================
# Streaming Expansion Protocol
# =============================================================================

@dataclass
class ExpansionChunk:
    """A chunk of expanded context for streaming"""
    chunk_id: int
    atoms: list[MemoryAtom]
    is_final: bool
    cumulative_tokens: int
    expansion_progress: float  # 0.0 to 1.0
    
    def to_dict(self) -> dict:
        return {
            'chunk_id': self.chunk_id,
            'atoms': [
                {
                    'content': a.content,
                    'type': str(a.type_sig),
                    'relevance': a.relevance_score,
                    'hash': a.content_hash
                }
                for a in self.atoms
            ],
            'is_final': self.is_final,
            'cumulative_tokens': self.cumulative_tokens,
            'progress': self.expansion_progress
        }


class StreamingExpander:
    """
    Async streaming expander for real-time context delivery.
    
    Yields chunks of expanded context as they become available,
    with backpressure support for flow control.
    """
    
    def __init__(
        self, 
        store: ContextStore,
        chunk_size: int = 10,
        max_tokens_per_chunk: int = 500
    ):
        self.store = store
        self.chunk_size = chunk_size
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self._base_expander = ExpanderFunctor(store)
    
    async def expand_stream(
        self,
        compressed: CompressedContext,
        relevance_threshold: float = 0.0
    ) -> AsyncIterator[ExpansionChunk]:
        """
        Stream expansion results as chunks.
        
        Implements a priority-based streaming where higher-relevance
        atoms are delivered first.
        """
        # First, do the full expansion (could be optimized for lazy eval)
        expanded = self._base_expander.expand(compressed)
        
        # Sort atoms by relevance for priority delivery
        sorted_atoms = sorted(
            expanded.atoms, 
            key=lambda a: -a.relevance_score
        )
        
        # Filter by threshold
        filtered_atoms = [
            a for a in sorted_atoms 
            if a.relevance_score >= relevance_threshold
        ]
        
        total_atoms = len(filtered_atoms)
        cumulative_tokens = 0
        chunk_id = 0
        
        # Stream chunks
        for i in range(0, total_atoms, self.chunk_size):
            chunk_atoms = filtered_atoms[i:i + self.chunk_size]
            chunk_tokens = sum(
                len(a.content.split()) * 13 // 10 
                for a in chunk_atoms
            )
            cumulative_tokens += chunk_tokens
            
            progress = min(1.0, (i + len(chunk_atoms)) / total_atoms)
            is_final = (i + self.chunk_size >= total_atoms)
            
            yield ExpansionChunk(
                chunk_id=chunk_id,
                atoms=chunk_atoms,
                is_final=is_final,
                cumulative_tokens=cumulative_tokens,
                expansion_progress=progress
            )
            
            chunk_id += 1
            
            # Yield control for backpressure
            await asyncio.sleep(0)


# =============================================================================
# Type-Safe Serialization
# =============================================================================

class ContextSerializer:
    """
    Type-safe serialization for context transfer.
    
    Preserves type information through serialization/deserialization,
    enabling type checking across process boundaries.
    """
    
    @staticmethod
    def serialize_atom(atom: MemoryAtom) -> dict:
        return {
            'content': atom.content,
            'type_sig': {
                'name': atom.type_sig.name,
                'kind': atom.type_sig.kind.name,
                'parameters': [
                    ContextSerializer._serialize_type_sig(p)
                    for p in atom.type_sig.parameters
                ],
                'constraints': list(atom.type_sig.constraints)
            },
            'timestamp': atom.timestamp.isoformat(),
            'source_hash': atom.source_hash,
            'relevance_score': atom.relevance_score
        }
    
    @staticmethod
    def _serialize_type_sig(sig: TypeSignature) -> dict:
        return {
            'name': sig.name,
            'kind': sig.kind.name,
            'parameters': [
                ContextSerializer._serialize_type_sig(p)
                for p in sig.parameters
            ],
            'constraints': list(sig.constraints)
        }
    
    @staticmethod
    def deserialize_atom(data: dict) -> MemoryAtom:
        return MemoryAtom(
            content=data['content'],
            type_sig=ContextSerializer._deserialize_type_sig(data['type_sig']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            source_hash=data['source_hash'],
            relevance_score=data['relevance_score']
        )
    
    @staticmethod
    def _deserialize_type_sig(data: dict) -> TypeSignature:
        return TypeSignature(
            name=data['name'],
            kind=Kind[data['kind']],
            parameters=tuple(
                ContextSerializer._deserialize_type_sig(p)
                for p in data['parameters']
            ),
            constraints=tuple(data['constraints'])
        )
    
    @staticmethod
    def serialize_compressed(ctx: CompressedContext) -> dict:
        return {
            'base_hash': ctx.base_hash,
            'delta_atoms': [
                ContextSerializer.serialize_atom(a) 
                for a in ctx.delta_atoms
            ],
            'delta_molecules': [
                ContextSerializer._serialize_molecule(m)
                for m in ctx.delta_molecules
            ],
            'removed_hashes': list(ctx.removed_hashes),
            'compression_metadata': ctx.compression_metadata
        }
    
    @staticmethod
    def _serialize_molecule(mol: MemoryMolecule) -> dict:
        return {
            'atoms': [
                ContextSerializer.serialize_atom(a) 
                for a in mol.atoms
            ],
            'relations': mol.relations,
            'molecule_type': ContextSerializer._serialize_type_sig(mol.molecule_type),
            'metadata': mol.metadata
        }
    
    @staticmethod
    def deserialize_compressed(data: dict) -> CompressedContext:
        return CompressedContext(
            base_hash=data['base_hash'],
            delta_atoms=[
                ContextSerializer.deserialize_atom(a)
                for a in data['delta_atoms']
            ],
            delta_molecules=[
                ContextSerializer._deserialize_molecule(m)
                for m in data['delta_molecules']
            ],
            removed_hashes=set(data['removed_hashes']),
            compression_metadata=data['compression_metadata']
        )
    
    @staticmethod
    def _deserialize_molecule(data: dict) -> MemoryMolecule:
        return MemoryMolecule(
            atoms=[
                ContextSerializer.deserialize_atom(a)
                for a in data['atoms']
            ],
            relations=data['relations'],
            molecule_type=ContextSerializer._deserialize_type_sig(data['molecule_type']),
            metadata=data['metadata']
        )


# =============================================================================
# Protocol Handler
# =============================================================================

class ExpansionProtocolHandler:
    """
    Handles the expansion protocol for client-server communication.
    
    Supports both request-response and streaming modes.
    """
    
    def __init__(self, store: ContextStore):
        self.store = store
        self.expander = ExpanderFunctor(store)
        self.streaming_expander = StreamingExpander(store)
        self._sequence_counter = 0
    
    async def handle_message(
        self, 
        msg: ProtocolMessage
    ) -> AsyncIterator[ProtocolMessage]:
        """Route and handle incoming protocol messages"""
        
        handlers = {
            MessageType.EXPAND_REQUEST: self._handle_expand,
            MessageType.STREAM_REQUEST: self._handle_stream,
            MessageType.QUERY_REQUEST: self._handle_query,
            MessageType.PUSH_CONTEXT: self._handle_push,
        }
        
        handler = handlers.get(msg.msg_type)
        if handler is None:
            yield self._error_response(msg.sequence_id, "Unknown message type")
            return
        
        async for response in handler(msg):
            yield response
    
    async def _handle_expand(
        self, 
        msg: ProtocolMessage
    ) -> AsyncIterator[ProtocolMessage]:
        """Handle full expansion request"""
        try:
            compressed = ContextSerializer.deserialize_compressed(msg.payload['context'])
            expanded = self.expander.expand(compressed)
            
            yield ProtocolMessage(
                MessageType.EXPAND_RESPONSE,
                msg.sequence_id,
                {
                    'atoms': [
                        ContextSerializer.serialize_atom(a)
                        for a in expanded.atoms
                    ],
                    'expansion_path': expanded.expansion_path,
                    'total_tokens': expanded.total_tokens_estimate,
                    'type_summary': expanded.type_summary
                }
            )
        except Exception as e:
            yield self._error_response(msg.sequence_id, str(e))
    
    async def _handle_stream(
        self, 
        msg: ProtocolMessage
    ) -> AsyncIterator[ProtocolMessage]:
        """Handle streaming expansion request"""
        try:
            compressed = ContextSerializer.deserialize_compressed(msg.payload['context'])
            threshold = msg.payload.get('relevance_threshold', 0.0)
            
            async for chunk in self.streaming_expander.expand_stream(
                compressed, 
                relevance_threshold=threshold
            ):
                yield ProtocolMessage(
                    MessageType.STREAM_CHUNK,
                    msg.sequence_id,
                    chunk.to_dict()
                )
            
            yield ProtocolMessage(
                MessageType.STREAM_END,
                msg.sequence_id,
                {'status': 'complete'}
            )
        except Exception as e:
            yield self._error_response(msg.sequence_id, str(e))
    
    async def _handle_query(
        self, 
        msg: ProtocolMessage
    ) -> AsyncIterator[ProtocolMessage]:
        """Handle context query request"""
        # Query implementation would go here
        yield self._error_response(msg.sequence_id, "Query not implemented")
    
    async def _handle_push(
        self, 
        msg: ProtocolMessage
    ) -> AsyncIterator[ProtocolMessage]:
        """Handle context push (store new context)"""
        try:
            compressed = ContextSerializer.deserialize_compressed(msg.payload['context'])
            hash_key = self.store.put(compressed)
            
            yield ProtocolMessage(
                MessageType.ACK,
                msg.sequence_id,
                {'hash': hash_key}
            )
        except Exception as e:
            yield self._error_response(msg.sequence_id, str(e))
    
    def _error_response(self, seq_id: int, error: str) -> ProtocolMessage:
        return ProtocolMessage(
            MessageType.ERROR,
            seq_id,
            {'error': error}
        )


# =============================================================================
# Merkle Tree for Context Integrity
# =============================================================================

@dataclass
class MerkleNode:
    """Node in the context Merkle tree"""
    hash: str
    left: Optional[MerkleNode] = None
    right: Optional[MerkleNode] = None
    data: Optional[MemoryAtom] = None
    
    @property
    def is_leaf(self) -> bool:
        return self.data is not None


class ContextMerkleTree:
    """
    Merkle tree for verifying context integrity.
    
    Enables efficient verification that a context has not been
    tampered with during transmission or storage.
    """
    
    def __init__(self, atoms: list[MemoryAtom]):
        self.atoms = atoms
        self.root = self._build_tree(atoms)
    
    def _build_tree(self, atoms: list[MemoryAtom]) -> Optional[MerkleNode]:
        if not atoms:
            return None
        
        # Create leaf nodes
        leaves = [
            MerkleNode(hash=a.content_hash, data=a)
            for a in atoms
        ]
        
        # Pad to power of 2
        while len(leaves) & (len(leaves) - 1):
            leaves.append(MerkleNode(hash='0' * 16))
        
        # Build tree bottom-up
        while len(leaves) > 1:
            next_level = []
            for i in range(0, len(leaves), 2):
                left, right = leaves[i], leaves[i + 1]
                combined = hashlib.sha256(
                    (left.hash + right.hash).encode()
                ).hexdigest()[:16]
                next_level.append(MerkleNode(
                    hash=combined,
                    left=left,
                    right=right
                ))
            leaves = next_level
        
        return leaves[0] if leaves else None
    
    @property
    def root_hash(self) -> str:
        return self.root.hash if self.root else '0' * 16
    
    def get_proof(self, atom: MemoryAtom) -> list[tuple[str, bool]]:
        """Get Merkle proof for an atom (hash, is_left)"""
        if not self.root:
            return []
        
        proof = []
        target_hash = atom.content_hash
        
        def find_and_build_proof(node: MerkleNode, target: str) -> bool:
            if node.is_leaf:
                return node.hash == target
            
            # Try left subtree
            if node.left and find_and_build_proof(node.left, target):
                if node.right:
                    proof.append((node.right.hash, False))
                return True
            
            # Try right subtree
            if node.right and find_and_build_proof(node.right, target):
                if node.left:
                    proof.append((node.left.hash, True))
                return True
            
            return False
        
        find_and_build_proof(self.root, target_hash)
        return proof
    
    def verify_proof(
        self, 
        atom_hash: str, 
        proof: list[tuple[str, bool]], 
        root_hash: str
    ) -> bool:
        """Verify a Merkle proof"""
        current = atom_hash
        for sibling_hash, is_left in proof:
            if is_left:
                combined = sibling_hash + current
            else:
                combined = current + sibling_hash
            current = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return current == root_hash


# =============================================================================
# Demo
# =============================================================================

async def demo_streaming():
    """Demo the streaming expansion"""
    from contextfs_expander import InMemoryContextStore
    
    store = InMemoryContextStore()
    streaming = StreamingExpander(store, chunk_size=2)
    
    # Create test context
    now = datetime.now()
    atoms = [
        MemoryAtom(f"Memory fact {i}", T_STRING, now, "test", 0.5 + i * 0.1)
        for i in range(10)
    ]
    
    ctx = CompressedContext(
        base_hash=None,
        delta_atoms=atoms,
        delta_molecules=[],
        removed_hashes=set(),
        compression_metadata={}
    )
    
    print("Streaming expansion:")
    print("-" * 40)
    
    async for chunk in streaming.expand_stream(ctx, relevance_threshold=0.6):
        print(f"Chunk {chunk.chunk_id}: {len(chunk.atoms)} atoms, "
              f"progress={chunk.expansion_progress:.0%}, "
              f"tokens={chunk.cumulative_tokens}")
        for atom in chunk.atoms:
            print(f"  [{atom.relevance_score:.2f}] {atom.content}")
    
    print("\nMerkle tree verification:")
    tree = ContextMerkleTree(atoms)
    print(f"Root hash: {tree.root_hash}")
    
    proof = tree.get_proof(atoms[0])
    verified = tree.verify_proof(atoms[0].content_hash, proof, tree.root_hash)
    print(f"Proof for atom 0: {'✓ verified' if verified else '✗ failed'}")


if __name__ == "__main__":
    asyncio.run(demo_streaming())
