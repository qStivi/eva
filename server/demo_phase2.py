"""
Phase 2 Demo - Database Models, Redis, and ChromaDB in Action
Demonstrates the two-track memory system.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal
from app.models import User, CharacterState, Conversation, ConversationTurn, Memory
from app.models.conversation import MessageRole
from app.redis_manager import redis_manager
from app.chroma_manager import chroma_manager
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


async def demo_two_track_memory():
    """Demonstrate the two-track memory architecture."""

    logger.info("=" * 70)
    logger.info("PHASE 2 DEMO: Two-Track Memory System")
    logger.info("=" * 70)

    # Connect to external services
    await redis_manager.connect()
    await chroma_manager.connect()

    async with AsyncSessionLocal() as session:
        # Get default user
        result = await session.execute(select(User).where(User.username == "default"))
        user = result.scalar_one()
        logger.info(f"\n✓ User: {user.username} ({user.id})")

        # Get default character state
        result = await session.execute(select(CharacterState).limit(1))
        character_state = result.scalar_one()
        logger.info(f"✓ Character State: {character_state.mood}")

        # Create a new conversation
        logger.info("\n" + "=" * 70)
        logger.info("TRACK 1: Creating Clean Conversation History")
        logger.info("=" * 70)

        conversation = Conversation(
            user_id=user.id,
            character_state_id=character_state.id,
            title="Demo Conversation",
            platform="demo",
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        logger.info(f"\n✓ Created conversation: {conversation.id}")

        # Add conversation turns (Track 1 - clean dialogue)
        turns_data = [
            ("user", "Hi Eva! I'm working on a new AI project."),
            ("assistant", "That sounds exciting! What kind of AI project are you building?"),
            ("user", "It's a character companion that journals and remembers conversations."),
            ("assistant", "Interesting! *jots down notes* I'd love to hear more about how the memory system works."),
            ("user", "It uses a two-track system - one for clean conversation, one for context."),
        ]

        for i, (role, content) in enumerate(turns_data):
            turn = ConversationTurn(
                conversation_id=conversation.id,
                role=MessageRole.USER if role == "user" else MessageRole.ASSISTANT,
                content=content,
                sequence=i,
            )
            session.add(turn)
            logger.info(f"  [{role:9}] {content}")

        await session.commit()

        # Store session state in Redis
        logger.info("\n" + "=" * 70)
        logger.info("REDIS: Session State Management")
        logger.info("=" * 70)

        session_data = {
            "conversation_id": str(conversation.id),
            "character_mood": character_state.mood,
            "platform": "demo",
            "last_message_time": datetime.now().isoformat(),
        }

        await redis_manager.set_session_data(
            str(user.id),
            str(conversation.id),
            session_data,
            ttl=3600
        )

        await redis_manager.set_active_conversation(str(user.id), str(conversation.id))

        logger.info(f"\n✓ Stored session data in Redis")
        logger.info(f"  Session key: session:{user.id}:{conversation.id}")
        logger.info(f"  TTL: 3600 seconds (1 hour)")

        # Retrieve session data
        retrieved_session = await redis_manager.get_session_data(
            str(user.id),
            str(conversation.id)
        )
        logger.info(f"\n✓ Retrieved session data:")
        for key, value in retrieved_session.items():
            logger.info(f"  {key}: {value}")

        # Get active conversation
        active_conv = await redis_manager.get_active_conversation(str(user.id))
        logger.info(f"\n✓ Active conversation for user: {active_conv}")

        # Create memories and embeddings (Track 2 - context)
        logger.info("\n" + "=" * 70)
        logger.info("TRACK 2: Creating Semantic Memories (ChromaDB)")
        logger.info("=" * 70)

        memories_to_add = [
            {
                "content": "User is working on an AI project - character companion with journaling",
                "metadata": {
                    "conversation_id": str(conversation.id),
                    "memory_type": "project",
                    "importance_score": 0.9,
                    "tags": "AI, project, companion",
                    "created_at": datetime.now().isoformat(),
                }
            },
            {
                "content": "User's project uses two-track memory system: clean conversation + context injection",
                "metadata": {
                    "conversation_id": str(conversation.id),
                    "memory_type": "technical_detail",
                    "importance_score": 0.85,
                    "tags": "memory system, architecture",
                    "created_at": datetime.now().isoformat(),
                }
            },
            {
                "content": "User is interested in memory systems and journaling AI",
                "metadata": {
                    "conversation_id": str(conversation.id),
                    "memory_type": "preference",
                    "importance_score": 0.7,
                    "tags": "interests, preferences",
                    "created_at": datetime.now().isoformat(),
                }
            },
        ]

        for mem_data in memories_to_add:
            # Add to ChromaDB
            embedding_id = await chroma_manager.add_memory(
                user_id=str(user.id),
                content=mem_data["content"],
                metadata=mem_data["metadata"],
            )

            # Create Memory record in PostgreSQL (links to ChromaDB)
            memory = Memory(
                user_id=user.id,
                conversation_id=conversation.id,
                embedding_id=embedding_id,
                content_summary=mem_data["content"],
                memory_type=mem_data["metadata"]["memory_type"],
                importance_score=mem_data["metadata"]["importance_score"],
                tags=mem_data["metadata"]["tags"],
            )
            session.add(memory)
            logger.info(f"\n✓ Added memory: {mem_data['content'][:60]}...")
            logger.info(f"  Embedding ID: {embedding_id}")
            logger.info(f"  Type: {mem_data['metadata']['memory_type']}")
            logger.info(f"  Importance: {mem_data['metadata']['importance_score']}")

        await session.commit()

        # Demonstrate semantic search
        logger.info("\n" + "=" * 70)
        logger.info("SEMANTIC SEARCH: Finding Relevant Memories")
        logger.info("=" * 70)

        queries = [
            "What project is the user working on?",
            "Tell me about memory systems",
            "What are the user's interests?",
        ]

        for query in queries:
            logger.info(f"\n🔍 Query: \"{query}\"")
            results = await chroma_manager.search_memories(
                user_id=str(user.id),
                query=query,
                n_results=2,
            )

            for i, result in enumerate(results, 1):
                logger.info(f"\n  Result {i}:")
                logger.info(f"    Content: {result['content'][:80]}...")
                logger.info(f"    Distance: {result['distance']:.4f} (lower = more similar)")
                logger.info(f"    Type: {result['metadata']['memory_type']}")

        # Show ChromaDB collection stats
        logger.info("\n" + "=" * 70)
        logger.info("STATISTICS")
        logger.info("=" * 70)

        stats = await chroma_manager.get_collection_stats(str(user.id))
        logger.info(f"\n✓ ChromaDB Collection: {stats['name']}")
        logger.info(f"  Total memories: {stats['count']}")

        # Count conversation turns
        result = await session.execute(
            select(ConversationTurn).where(ConversationTurn.conversation_id == conversation.id)
        )
        turns = result.scalars().all()
        logger.info(f"\n✓ Conversation: {conversation.title}")
        logger.info(f"  Total turns: {len(turns)}")

        # Test caching
        logger.info("\n" + "=" * 70)
        logger.info("REDIS CACHING")
        logger.info("=" * 70)

        cache_data = {
            "character_mood": character_state.mood,
            "preferences": character_state.preferences,
        }
        await redis_manager.set_cache("character_state", str(character_state.id), cache_data)
        logger.info(f"\n✓ Cached character state")

        cached = await redis_manager.get_cache("character_state", str(character_state.id))
        logger.info(f"✓ Retrieved from cache: {cached}")

    # Cleanup
    await redis_manager.disconnect()

    logger.info("\n" + "=" * 70)
    logger.info("DEMO COMPLETE!")
    logger.info("=" * 70)
    logger.info("\nThis demonstrated:")
    logger.info("  ✓ Track 1: Clean conversation history (PostgreSQL)")
    logger.info("  ✓ Track 2: Semantic memories (PostgreSQL + ChromaDB)")
    logger.info("  ✓ Redis: Session state and caching")
    logger.info("  ✓ Vector search: Finding relevant context")
    logger.info("\nThe two-track system keeps conversation clean while")
    logger.info("maintaining rich contextual memory for intelligent responses!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_two_track_memory())
