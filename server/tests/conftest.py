"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.character import CharacterState
from app.models.conversation import Conversation


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    settings.debug = True
    settings.database_url = "sqlite:///:memory:"
    return settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine):
    """Create async database session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def client():
    """
    Create a test client for FastAPI.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def sample_user(async_session):
    """Create a sample user for testing."""
    user = User(
        username="testuser",
        display_name="Test User",
        is_active=True,
        preferences={},
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def sample_user_with_prefs(async_session):
    """Create a sample user with preferences for testing."""
    user = User(
        username="testuser_prefs",
        display_name="Alice",
        is_active=True,
        preferences={
            "theme": "dark",
            "notifications_enabled": True,
            "favorite_color": "blue",
        },
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def sample_character_state(async_session):
    """Create a sample character state for testing."""
    character_state = CharacterState(
        mood="happy",
        mood_context="User shared good news",
        preferences={
            "conversation_style": "casual",
            "emoji_usage": "moderate",
        },
        goals={},
    )
    async_session.add(character_state)
    await async_session.commit()
    await async_session.refresh(character_state)
    return character_state


@pytest.fixture(scope="function")
async def sample_conversation(async_session, sample_user, sample_character_state):
    """Create a sample conversation for testing."""
    conversation = Conversation(
        user_id=sample_user.id,
        character_state_id=sample_character_state.id,
        title="Test Conversation",
        platform="test",
    )
    async_session.add(conversation)
    await async_session.commit()
    await async_session.refresh(conversation)
    return conversation
