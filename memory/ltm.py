"""Long-Term Memory (LTM) implementation for Cognitive Memory System."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import hashlib
import numpy as np

# Try to import chromadb, fallback to simple JSON storage
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

# Try to import sentence-transformers for embeddings
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


@dataclass
class MemoryItem:
    """Represents a single long-term memory item."""
    
    id: str
    content: str
    memory_type: str  # "fact", "conversation", "preference", "task"
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryItem":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            metadata=data.get("metadata", {}),
        )
    
    def access(self) -> None:
        """Record an access to this memory."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class LongTermMemory:
    """
    Long-Term Memory for persistent knowledge storage.
    
    Uses ChromaDB for vector storage if available,
    otherwise falls back to simple JSON-based storage.
    """
    
    def __init__(
        self,
        storage_path: Path,
        collection_name: str = "cognitive_memory",
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize LTM.
        
        Args:
            storage_path: Path for storing memory data
            collection_name: Name of the vector collection
            embedding_model: Sentence transformer model name
            top_k: Default number of memories to retrieve
            similarity_threshold: Minimum similarity for retrieval
        """
        self.storage_path = Path(storage_path)
        self.collection_name = collection_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Ensure storage path exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        self._embedding_model = None
        self._embedding_model_name = embedding_model
        
        # Initialize storage backend
        self._use_chromadb = HAS_CHROMADB
        self._chroma_client = None
        self._collection = None
        self._json_storage: dict[str, MemoryItem] = {}
        
        self._init_storage()
    
    def _init_storage(self) -> None:
        """Initialize the storage backend."""
        if self._use_chromadb:
            try:
                self._chroma_client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=str(self.storage_path / "chroma"),
                    anonymized_telemetry=False,
                ))
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                print("Using ChromaDB for LTM storage")
            except Exception as e:
                print(f"ChromaDB initialization failed: {e}")
                self._use_chromadb = False
        
        if not self._use_chromadb:
            # Fallback to JSON storage
            self._json_path = self.storage_path / "ltm_storage.json"
            self._load_json_storage()
            print("Using JSON file for LTM storage")
    
    def _get_embedding_model(self) -> Optional["SentenceTransformer"]:
        """Get or load embedding model."""
        if not HAS_SENTENCE_TRANSFORMERS:
            return None
        
        if self._embedding_model is None:
            print(f"Loading embedding model: {self._embedding_model_name}")
            self._embedding_model = SentenceTransformer(self._embedding_model_name)
        
        return self._embedding_model
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for content."""
        timestamp = datetime.now().isoformat()
        hash_input = f"{content}:{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _get_embedding(self, text: str) -> Optional[list[float]]:
        """Get embedding vector for text."""
        model = self._get_embedding_model()
        if model is None:
            return None
        
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def store(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        Store a new memory.
        
        Args:
            content: Memory content
            memory_type: Type of memory (fact, conversation, preference, task)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            Created memory item
        """
        memory_id = self._generate_id(content)
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {},
        )
        
        # Get embedding
        embedding = self._get_embedding(content)
        memory.embedding = embedding
        
        if self._use_chromadb and self._collection is not None:
            # Store in ChromaDB
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[{
                    "memory_type": memory_type,
                    "importance": importance,
                    "timestamp": memory.timestamp.isoformat(),
                    **(metadata or {}),
                }],
                embeddings=[embedding] if embedding else None,
            )
        else:
            # Store in JSON
            self._json_storage[memory_id] = memory
            self._save_json_storage()
        
        return memory
    
    def retrieve(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory item or None if not found
        """
        if self._use_chromadb and self._collection is not None:
            results = self._collection.get(ids=[memory_id])
            if results["ids"]:
                doc = results["documents"][0]
                meta = results["metadatas"][0]
                return MemoryItem(
                    id=memory_id,
                    content=doc,
                    memory_type=meta.get("memory_type", "fact"),
                    importance=meta.get("importance", 0.5),
                    timestamp=datetime.fromisoformat(meta.get("timestamp", datetime.now().isoformat())),
                    metadata={k: v for k, v in meta.items() if k not in ["memory_type", "importance", "timestamp"]},
                )
        else:
            memory = self._json_storage.get(memory_id)
            if memory:
                memory.access()
                self._save_json_storage()
            return memory
        
        return None
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Search for relevant memories.
        
        Args:
            query: Search query
            top_k: Number of results to return
            memory_type: Filter by memory type
            min_importance: Minimum importance threshold
            
        Returns:
            List of (memory, similarity_score) tuples
        """
        k = top_k or self.top_k
        results = []
        
        if self._use_chromadb and self._collection is not None:
            # Build where filter
            where = {}
            if memory_type:
                where["memory_type"] = memory_type
            if min_importance > 0:
                where["importance"] = {"$gte": min_importance}
            
            # Query ChromaDB
            query_embedding = self._get_embedding(query)
            chroma_results = self._collection.query(
                query_embeddings=[query_embedding] if query_embedding else None,
                query_texts=[query] if not query_embedding else None,
                n_results=k,
                where=where if where else None,
            )
            
            if chroma_results["ids"] and chroma_results["ids"][0]:
                for i, memory_id in enumerate(chroma_results["ids"][0]):
                    doc = chroma_results["documents"][0][i]
                    meta = chroma_results["metadatas"][0][i]
                    distance = chroma_results["distances"][0][i] if chroma_results.get("distances") else 0
                    
                    # Convert distance to similarity (cosine distance to similarity)
                    similarity = 1 - distance
                    
                    if similarity >= self.similarity_threshold:
                        memory = MemoryItem(
                            id=memory_id,
                            content=doc,
                            memory_type=meta.get("memory_type", "fact"),
                            importance=meta.get("importance", 0.5),
                            timestamp=datetime.fromisoformat(meta.get("timestamp", datetime.now().isoformat())),
                            metadata={k: v for k, v in meta.items() if k not in ["memory_type", "importance", "timestamp"]},
                        )
                        results.append((memory, similarity))
        else:
            # JSON-based search with embeddings
            query_embedding = self._get_embedding(query)
            
            for memory in self._json_storage.values():
                # Filter by type and importance
                if memory_type and memory.memory_type != memory_type:
                    continue
                if memory.importance < min_importance:
                    continue
                
                # Calculate similarity
                if query_embedding and memory.embedding:
                    similarity = self._cosine_similarity(query_embedding, memory.embedding)
                else:
                    # Fallback to simple keyword matching
                    similarity = self._keyword_similarity(query, memory.content)
                
                if similarity >= self.similarity_threshold:
                    results.append((memory, similarity))
            
            # Sort by similarity and take top-k
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:k]
        
        # Update access counts
        for memory, _ in results:
            memory.access()
        
        if not self._use_chromadb:
            self._save_json_storage()
        
        return results
    
    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
    
    def _keyword_similarity(self, query: str, content: str) -> float:
        """Simple keyword-based similarity."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words or not content_words:
            return 0.0
        
        intersection = query_words & content_words
        union = query_words | content_words
        
        return len(intersection) / len(union)
    
    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory.
        
        Args:
            memory_id: Memory ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self._use_chromadb and self._collection is not None:
            try:
                self._collection.delete(ids=[memory_id])
                return True
            except Exception:
                return False
        else:
            if memory_id in self._json_storage:
                del self._json_storage[memory_id]
                self._save_json_storage()
                return True
        
        return False
    
    def get_all(self, memory_type: Optional[str] = None) -> list[MemoryItem]:
        """
        Get all memories, optionally filtered by type.
        
        Args:
            memory_type: Optional type filter
            
        Returns:
            List of memory items
        """
        memories = []
        
        if self._use_chromadb and self._collection is not None:
            where = {"memory_type": memory_type} if memory_type else None
            results = self._collection.get(where=where)
            
            for i, memory_id in enumerate(results["ids"]):
                doc = results["documents"][i]
                meta = results["metadatas"][i]
                
                memory = MemoryItem(
                    id=memory_id,
                    content=doc,
                    memory_type=meta.get("memory_type", "fact"),
                    importance=meta.get("importance", 0.5),
                    timestamp=datetime.fromisoformat(meta.get("timestamp", datetime.now().isoformat())),
                    metadata={k: v for k, v in meta.items() if k not in ["memory_type", "importance", "timestamp"]},
                )
                memories.append(memory)
        else:
            for memory in self._json_storage.values():
                if memory_type is None or memory.memory_type == memory_type:
                    memories.append(memory)
        
        return memories
    
    def count(self) -> int:
        """Get total number of memories."""
        if self._use_chromadb and self._collection is not None:
            return self._collection.count()
        else:
            return len(self._json_storage)
    
    def _load_json_storage(self) -> None:
        """Load memories from JSON file."""
        if self._json_path.exists():
            with open(self._json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._json_storage = {
                    k: MemoryItem.from_dict(v) for k, v in data.items()
                }
    
    def _save_json_storage(self) -> None:
        """Save memories to JSON file."""
        data = {k: v.to_dict() for k, v in self._json_storage.items()}
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def clear(self) -> None:
        """Clear all memories."""
        if self._use_chromadb and self._collection is not None:
            # Delete and recreate collection
            self._chroma_client.delete_collection(self.collection_name)
            self._collection = self._chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self._json_storage.clear()
            self._save_json_storage()
