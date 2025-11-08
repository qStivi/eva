"""
Memory Retrieval (RAG Implementation)

Manages semantic memory storage and retrieval using ChromaDB.
This module handles the ingestion of conversation turns as memories
and semantic search for relevant context.

Key features:
- Ingest conversation turns as searchable memories
- Calculate importance scores for memory prioritization
- Semantic search with ChromaDB embeddings
- Filter and rank memories by relevance, importance, and recency
- Manage memory lifecycle (creation, retrieval, potential pruning)
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.models.conversation import ConversationTurn, MessageRole
from app.chroma_manager import ChromaManager


class MemoryRetrieval:
    """
    Handles memory ingestion and semantic retrieval.

    This class implements the RAG (Retrieval-Augmented Generation) pattern
    for Eva's memory system. It:
    1. Analyzes conversation turns for importance
    2. Creates semantic embeddings via ChromaDB
    3. Stores memories in both ChromaDB (vectors) and PostgreSQL (metadata)
    4. Retrieves relevant memories via semantic similarity search
    """

    def __init__(
        self,
        min_relevance_score: float = 0.5,
        max_memories: int = 10,
        min_importance_for_storage: float = 0.3,
        recency_weight: float = 0.2,
    ):
        """
        Initialize memory retrieval system.

        Args:
            min_relevance_score: Minimum similarity score for retrieval (0.0-1.0)
            max_memories: Maximum number of memories to retrieve
            min_importance_for_storage: Minimum importance to store a memory
            recency_weight: Weight for recency in re-ranking (0.0-1.0)
        """
        self.min_relevance_score = min_relevance_score
        self.max_memories = max_memories
        self.min_importance_for_storage = min_importance_for_storage
        self.recency_weight = recency_weight
        self.chroma_manager = ChromaManager()

    async def ingest_conversation_turn(
        self,
        session: AsyncSession,
        user_id: str,
        conversation_id: str,
        turn: ConversationTurn,
        force: bool = False,
    ) -> Optional[str]:
        """
        Process a conversation turn and potentially store it as a memory.

        This is the main ingestion pipeline:
        1. Analyze if turn is worth remembering
        2. Extract summary/key points
        3. Calculate importance score
        4. Generate embedding via ChromaDB
        5. Store in both ChromaDB and PostgreSQL

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            conversation_id: Conversation ID (UUID as string)
            turn: ConversationTurn object to potentially store
            force: If True, skip importance check and always store

        Returns:
            Memory embedding_id if stored, None if skipped
        """
        # Calculate importance score
        importance = self.calculate_importance_score(turn)

        # Skip low-importance turns unless forced
        if not force and importance < self.min_importance_for_storage:
            return None

        # Extract content summary
        content_summary = self._extract_summary(turn)

        # Determine memory type
        memory_type = self._determine_memory_type(turn)

        # Generate embedding and store in ChromaDB
        metadata = {
            "conversation_id": str(conversation_id),
            "role": turn.role.value,
            "sequence": turn.sequence,
            "timestamp": turn.timestamp.isoformat() if turn.timestamp else datetime.now().isoformat(),
            "importance_score": importance,
            "memory_type": memory_type,
        }

        embedding_id = await self.chroma_manager.add_memory(
            user_id=user_id,
            content=content_summary,
            metadata=metadata,
        )

        # Store metadata in PostgreSQL
        memory = Memory(
            user_id=UUID(user_id),
            conversation_id=UUID(conversation_id),
            embedding_id=embedding_id,
            content_summary=content_summary,
            memory_type=memory_type,
            importance_score=importance,
        )

        session.add(memory)
        await session.commit()
        await session.refresh(memory)

        return embedding_id

    async def search_relevant_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 10,
        filter_by_recency: bool = False,
        recency_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic similarity.

        Args:
            user_id: User ID (UUID as string)
            query: Search query (usually the user's latest message)
            n_results: Number of results to return
            filter_by_recency: If True, only return memories from last N days
            recency_days: Number of days to look back (if filter_by_recency=True)

        Returns:
            List of memory dicts with keys:
                - content_summary: The memory content
                - importance_score: Importance score (0.0-1.0)
                - distance: Similarity distance from query
                - created_at: When the memory was created
                - memory_type: Type of memory
                - embedding_id: ChromaDB embedding ID
        """
        # Search ChromaDB for semantically similar memories
        search_results = await self.chroma_manager.search_memories(
            user_id=user_id,
            query=query,
            n_results=n_results * 2,  # Get extra for filtering/re-ranking
        )

        if not search_results:
            return []

        # Convert ChromaDB results to our format
        memories = []
        for result in search_results:
            # Extract metadata
            metadata = result.get("metadata", {})
            distance = result.get("distance", 1.0)

            # Calculate similarity score (inverse of distance)
            # ChromaDB uses L2 distance, convert to similarity (0-1)
            similarity = 1.0 / (1.0 + distance)

            # Skip if below relevance threshold
            if similarity < self.min_relevance_score:
                continue

            # Parse timestamp
            timestamp_str = metadata.get("timestamp")
            created_at = datetime.fromisoformat(timestamp_str) if timestamp_str else None

            # Filter by recency if requested
            if filter_by_recency and created_at:
                cutoff = datetime.now() - timedelta(days=recency_days)
                if created_at < cutoff:
                    continue

            # Build memory dict
            memory = {
                "content_summary": result.get("document", ""),
                "importance_score": metadata.get("importance_score", 0.5),
                "distance": distance,
                "similarity": similarity,
                "created_at": created_at,
                "memory_type": metadata.get("memory_type", "conversation"),
                "embedding_id": result.get("id", ""),
                "conversation_id": metadata.get("conversation_id"),
            }

            memories.append(memory)

        # Re-rank by multiple factors
        ranked_memories = self.rank_memories(memories)

        # Return top N
        return ranked_memories[:n_results]

    def calculate_importance_score(
        self,
        turn: ConversationTurn,
    ) -> float:
        """
        Calculate importance score for a conversation turn.

        This heuristic determines whether a turn is worth storing as a memory.
        Higher scores indicate more important information.

        Factors considered:
        - Length (longer messages often contain more information)
        - Role (user messages often more important than responses)
        - Keywords indicating important information
        - Questions vs statements
        - Emotional indicators

        Args:
            turn: ConversationTurn object to score

        Returns:
            Importance score between 0.0 and 1.0
        """
        content = turn.content.lower()
        score = 0.3  # Base score

        # Length factor (longer messages often more important)
        word_count = len(content.split())
        if word_count > 50:
            score += 0.2
        elif word_count > 20:
            score += 0.1

        # Role factor (user messages often contain new information)
        if turn.role == MessageRole.USER:
            score += 0.1

        # Keyword indicators (important information)
        important_keywords = [
            "remember", "important", "favorite", "love", "hate",
            "always", "never", "prefer", "like", "dislike",
            "work", "job", "family", "friend", "project",
            "goal", "plan", "want", "need", "wish",
        ]

        keyword_matches = sum(1 for keyword in important_keywords if keyword in content)
        score += min(keyword_matches * 0.05, 0.2)

        # Question indicator (questions about user often important)
        if "?" in content and turn.role == MessageRole.ASSISTANT:
            score += 0.05

        # Personal information indicators
        personal_indicators = ["my ", "i am", "i'm", "i have", "i've", "i work", "i live"]
        if any(indicator in content for indicator in personal_indicators):
            score += 0.15

        # Emotional indicators (emotional moments are memorable)
        emotional_words = ["feel", "feeling", "emotion", "happy", "sad", "angry", "excited", "worried"]
        if any(word in content for word in emotional_words):
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    def rank_memories(
        self,
        memories: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Re-rank memories by multiple factors.

        Combines semantic similarity, importance score, and recency
        to produce a final ranking.

        Args:
            memories: List of memory dicts with similarity and importance

        Returns:
            Re-ranked list of memories
        """
        # Calculate composite score for each memory
        for memory in memories:
            similarity = memory.get("similarity", 0.5)
            importance = memory.get("importance_score", 0.5)
            created_at = memory.get("created_at")

            # Recency factor (newer memories slightly preferred)
            recency_factor = 0.5
            if created_at:
                days_old = (datetime.now() - created_at).days
                # Exponential decay: 1.0 at day 0, 0.5 at 30 days, 0.25 at 60 days
                recency_factor = 1.0 / (1.0 + (days_old / 30.0))

            # Composite score: weighted combination
            composite = (
                similarity * (1.0 - self.recency_weight) +
                importance * 0.3 +
                recency_factor * self.recency_weight
            )

            memory["composite_score"] = composite

        # Sort by composite score (descending)
        ranked = sorted(
            memories,
            key=lambda m: m.get("composite_score", 0.0),
            reverse=True,
        )

        return ranked

    def _extract_summary(
        self,
        turn: ConversationTurn,
    ) -> str:
        """
        Extract a summary from a conversation turn.

        For now, this just returns the content as-is.
        In the future, this could use LLM-based summarization
        for very long messages.

        Args:
            turn: ConversationTurn object

        Returns:
            Summary string
        """
        # TODO (Phase 6+): Implement LLM-based summarization for long turns
        content = turn.content

        # For now, truncate very long messages
        max_length = 500
        if len(content) > max_length:
            return content[:max_length] + "..."

        return content

    def _determine_memory_type(
        self,
        turn: ConversationTurn,
    ) -> str:
        """
        Determine the type of memory from a conversation turn.

        Memory types help with filtering and organization:
        - "conversation": General conversation
        - "fact": User-stated facts about themselves
        - "preference": User preferences or opinions
        - "event": Specific events or experiences
        - "plan": Future plans or goals

        Args:
            turn: ConversationTurn object

        Returns:
            Memory type string
        """
        content = turn.content.lower()

        # Fact indicators
        fact_indicators = ["i am", "i'm", "my name is", "i have", "i've", "i work"]
        if any(indicator in content for indicator in fact_indicators):
            return "fact"

        # Preference indicators
        pref_indicators = ["i like", "i love", "i prefer", "i hate", "i dislike", "favorite"]
        if any(indicator in content for indicator in pref_indicators):
            return "preference"

        # Plan indicators
        plan_indicators = ["i will", "i'll", "going to", "planning to", "want to", "goal"]
        if any(indicator in content for indicator in plan_indicators):
            return "plan"

        # Event indicators
        event_indicators = ["yesterday", "today", "last week", "happened", "went to", "did"]
        if any(indicator in content for indicator in event_indicators):
            return "event"

        # Default
        return "conversation"

    async def delete_memory(
        self,
        session: AsyncSession,
        memory_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a memory from both PostgreSQL and ChromaDB.

        Args:
            session: Database session
            memory_id: Memory UUID (primary key)
            user_id: User ID (for ChromaDB collection)

        Returns:
            True if deleted, False if not found
        """
        # Load memory from PostgreSQL
        result = await session.execute(
            select(Memory).where(Memory.id == UUID(memory_id))
        )
        memory = result.scalar_one_or_none()

        if not memory:
            return False

        # Delete from ChromaDB
        await self.chroma_manager.delete_memory(
            user_id=user_id,
            memory_id=memory.embedding_id,
        )

        # Delete from PostgreSQL
        await session.delete(memory)
        await session.commit()

        return True

    async def get_memory_stats(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get statistics about stored memories for a user.

        Args:
            session: Database session
            user_id: User ID (UUID as string)

        Returns:
            Dict with memory statistics
        """
        # Count memories by type
        result = await session.execute(
            select(Memory).where(Memory.user_id == UUID(user_id))
        )
        memories = result.scalars().all()

        # Calculate stats
        stats = {
            "total_memories": len(memories),
            "by_type": {},
            "average_importance": 0.0,
            "oldest_memory": None,
            "newest_memory": None,
        }

        if not memories:
            return stats

        # Group by type
        for memory in memories:
            mem_type = memory.memory_type
            stats["by_type"][mem_type] = stats["by_type"].get(mem_type, 0) + 1

        # Average importance
        total_importance = sum(m.importance_score for m in memories)
        stats["average_importance"] = total_importance / len(memories)

        # Oldest and newest
        sorted_by_date = sorted(memories, key=lambda m: m.created_at)
        stats["oldest_memory"] = sorted_by_date[0].created_at
        stats["newest_memory"] = sorted_by_date[-1].created_at

        return stats
