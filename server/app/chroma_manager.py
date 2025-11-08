"""
ChromaDB manager for vector memory storage and semantic search.
Manages embeddings for Track 2 (context injection) of the two-track memory system.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


class ChromaManager:
    """
    ChromaDB manager for semantic memory search.

    Collections are organized per user: user_{user_id}_memories

    Each document stores:
    - id: UUID matching Memory.embedding_id in PostgreSQL
    - embedding: Vector representation of memory content
    - metadata: {conversation_id, memory_type, importance_score, tags, created_at}
    - document: The actual content summary text
    """

    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.embedding_model: Optional[SentenceTransformer] = None
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"  # 384-dim, fast

    async def connect(self):
        """Initialize ChromaDB client and embedding model."""
        try:
            # Connect to ChromaDB server
            self.client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )

            # Test connection
            self.client.heartbeat()

            # Load embedding model (lazy loading - only when needed)
            logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")

        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise

    def _load_embedding_model(self):
        """Load sentence transformer model (lazy loading)."""
        if self.embedding_model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.embedding_model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

    def _get_collection_name(self, user_id: str) -> str:
        """Get ChromaDB collection name for a user."""
        return f"user_{user_id}_memories"

    def _get_or_create_collection(self, user_id: str):
        """Get or create a ChromaDB collection for a user."""
        collection_name = self._get_collection_name(user_id)
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"user_id": user_id},
        )

    async def add_memory(
        self,
        user_id: str,
        content: str,
        metadata: Dict[str, Any],
        memory_id: Optional[str] = None,
    ) -> str:
        """
        Add a memory to the vector database.

        Args:
            user_id: User ID
            content: Memory content to embed
            metadata: Metadata dict (conversation_id, memory_type, importance_score, etc.)
            memory_id: Optional UUID (will generate if not provided)

        Returns:
            The memory ID (UUID string)
        """
        try:
            # Load embedding model if needed
            self._load_embedding_model()

            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()

            # Generate ID if not provided
            if memory_id is None:
                memory_id = str(uuid.uuid4())

            # Get user's collection
            collection = self._get_or_create_collection(user_id)

            # Add to ChromaDB
            collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
            )

            logger.info(f"Added memory {memory_id} for user {user_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def search_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic similarity.

        Args:
            user_id: User ID
            query: Query text to search for
            n_results: Number of results to return (default 10)
            where: Optional metadata filter (e.g., {"memory_type": "conversation"})

        Returns:
            List of memory dicts with keys: id, content, metadata, distance
        """
        try:
            # Load embedding model if needed
            self._load_embedding_model()

            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()

            # Get user's collection
            collection = self._get_or_create_collection(user_id)

            # Search ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
            )

            # Format results
            memories = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    memories.append({
                        "id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                    })

            logger.info(f"Found {len(memories)} memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    async def get_memory(self, user_id: str, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID.

        Args:
            user_id: User ID
            memory_id: Memory ID (UUID)

        Returns:
            Memory dict or None if not found
        """
        try:
            collection = self._get_or_create_collection(user_id)
            result = collection.get(ids=[memory_id])

            if result["ids"]:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0],
                }
            return None

        except Exception as e:
            logger.error(f"Failed to get memory: {e}")
            return None

    async def update_memory(
        self,
        user_id: str,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update a memory's content and/or metadata.

        Args:
            user_id: User ID
            memory_id: Memory ID
            content: New content (will re-embed if provided)
            metadata: New metadata (will merge with existing)

        Returns:
            True if successful
        """
        try:
            collection = self._get_or_create_collection(user_id)

            update_kwargs = {"ids": [memory_id]}

            # Update content and re-embed if provided
            if content is not None:
                self._load_embedding_model()
                embedding = self.embedding_model.encode(content).tolist()
                update_kwargs["embeddings"] = [embedding]
                update_kwargs["documents"] = [content]

            # Update metadata if provided
            if metadata is not None:
                update_kwargs["metadatas"] = [metadata]

            collection.update(**update_kwargs)
            logger.info(f"Updated memory {memory_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            user_id: User ID
            memory_id: Memory ID

        Returns:
            True if successful
        """
        try:
            collection = self._get_or_create_collection(user_id)
            collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory {memory_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    async def delete_user_memories(self, user_id: str) -> bool:
        """
        Delete all memories for a user (delete collection).

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            collection_name = self._get_collection_name(user_id)
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted all memories for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete user memories: {e}")
            return False

    async def get_collection_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about a user's memory collection.

        Args:
            user_id: User ID

        Returns:
            Dict with count and other stats
        """
        try:
            collection = self._get_or_create_collection(user_id)
            return {
                "user_id": user_id,
                "count": collection.count(),
                "name": collection.name,
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"user_id": user_id, "count": 0, "error": str(e)}


# Global ChromaDB manager instance
chroma_manager = ChromaManager()


async def get_chroma() -> ChromaManager:
    """
    Dependency for FastAPI routes to get ChromaDB manager.

    Usage:
        @app.get("/endpoint")
        async def endpoint(chroma: ChromaManager = Depends(get_chroma)):
            # Use chroma here
    """
    return chroma_manager
