"""
Database initialization script.
Creates default user and character state for development/testing.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import AsyncSessionLocal, init_db
from app.models import User, CharacterState
from app.redis_manager import redis_manager
from app.chroma_manager import chroma_manager
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_default_user(session) -> User:
    """Create default development user."""
    from sqlalchemy import select

    # Check if default user exists
    result = await session.execute(select(User).where(User.username == "default"))
    user = result.scalar_one_or_none()

    if user:
        logger.info(f"Default user already exists: {user.username} ({user.id})")
        return user

    # Create new default user
    user = User(
        username="default",
        display_name="Default User",
        preferences={
            "theme": "dark",
            "notifications_enabled": True,
        },
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info(f"Created default user: {user.username} ({user.id})")
    return user


async def create_default_character_state(session) -> CharacterState:
    """Create default character state for Eva."""
    from sqlalchemy import select

    # Check if default character state exists
    result = await session.execute(
        select(CharacterState).where(CharacterState.mood == settings.default_mood)
    )
    character_state = result.scalar_one_or_none()

    if character_state:
        logger.info(f"Default character state already exists ({character_state.id})")
        return character_state

    # Create new default character state
    character_state = CharacterState(
        mood=settings.default_mood,
        mood_context="Initial state",
        preferences={
            "communication_style": "friendly and thoughtful",
            "journaling_style": "reflective",
        },
        goals={},
    )
    session.add(character_state)
    await session.commit()
    await session.refresh(character_state)

    logger.info(f"Created default character state: {character_state.mood} ({character_state.id})")
    return character_state


async def initialize_database():
    """Initialize database with default data."""
    logger.info("Starting database initialization...")

    try:
        # Create all tables
        logger.info("Creating database tables...")
        await init_db()

        # Create default data
        async with AsyncSessionLocal() as session:
            logger.info("Creating default user...")
            user = await create_default_user(session)

            logger.info("Creating default character state...")
            character_state = await create_default_character_state(session)

        logger.info("✓ Database initialization complete!")
        logger.info(f"  - Default user: {user.username} ({user.id})")
        logger.info(f"  - Default character state: {character_state.mood} ({character_state.id})")

    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise


async def test_redis_connection():
    """Test Redis connection."""
    try:
        logger.info("Testing Redis connection...")
        await redis_manager.connect()
        is_connected = await redis_manager.ping()
        if is_connected:
            logger.info("✓ Redis connection successful")
        else:
            logger.warning("✗ Redis connection failed")
        await redis_manager.disconnect()
    except Exception as e:
        logger.error(f"✗ Redis connection error: {e}")


async def test_chromadb_connection():
    """Test ChromaDB connection."""
    try:
        logger.info("Testing ChromaDB connection...")
        await chroma_manager.connect()
        # Test with a sample collection
        stats = await chroma_manager.get_collection_stats("test_user")
        logger.info(f"✓ ChromaDB connection successful (test collection: {stats['count']} items)")
    except Exception as e:
        logger.error(f"✗ ChromaDB connection error: {e}")


async def main():
    """Main initialization function."""
    logger.info("=" * 60)
    logger.info("Eva Character Companion - Database Initialization")
    logger.info("=" * 60)

    # Initialize database
    await initialize_database()

    # Test connections
    logger.info("\nTesting external connections...")
    await test_redis_connection()
    await test_chromadb_connection()

    logger.info("\n" + "=" * 60)
    logger.info("Initialization complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
