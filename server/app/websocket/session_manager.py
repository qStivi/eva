"""
WebSocket session manager.

Manages WebSocket session state with Redis, including session initialization,
retrieval, and cleanup.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.redis_manager import redis_manager
from app.models.user import User
from app.models.character import CharacterState
from app.models.conversation import Conversation

logger = logging.getLogger(__name__)

# Session TTL: 1 hour of inactivity
SESSION_TTL_SECONDS = 3600

# Hardcoded user for MVP (same as terminal)
WEBSOCKET_USER = {
    "username": "qStivi",
    "display_name": "Stephan",
}


class WebSocketSessionManager:
    """
    Manages WebSocket session state with Redis.

    Each WebSocket connection gets a session stored in Redis with:
    - User ID
    - Conversation ID
    - Character state ID
    - Connection metadata

    Sessions auto-expire after TTL for cleanup.
    """

    def __init__(self):
        """Initialize session manager."""
        logger.info("WebSocketSessionManager initialized")

    def _get_session_key(self, connection_id: str) -> str:
        """
        Get Redis key for a connection's session.

        Args:
            connection_id: WebSocket connection ID

        Returns:
            Redis key string
        """
        return f"websocket:session:{connection_id}"

    async def _ensure_redis(self):
        """Ensure Redis client is initialized."""
        if redis_manager.redis_client is None:
            await redis_manager.connect()

    async def create_session(
        self,
        connection_id: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Initialize WebSocket session.

        Loads or creates user, character state, and conversation (just like
        terminal interface). Stores session state in Redis.

        Args:
            connection_id: WebSocket connection ID
            db_session: Database session

        Returns:
            Session data dictionary with user, conversation, character_state IDs
        """
        await self._ensure_redis()

        # Load or create user (hardcoded for MVP)
        user = await self._load_or_create_user(db_session)

        # Load character state
        character_state = await self._load_character_state(db_session)

        # Load or create conversation
        conversation = await self._load_or_create_conversation(
            db_session, user, character_state
        )

        # Build session data
        session_data = {
            "user_id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "conversation_id": str(conversation.id),
            "character_state_id": str(character_state.id),
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
        }

        # Store in Redis with TTL
        session_key = self._get_session_key(connection_id)
        await redis_manager.redis_client.setex(
            session_key,
            SESSION_TTL_SECONDS,
            json.dumps(session_data)
        )

        logger.info(
            f"Created WebSocket session: {connection_id} "
            f"(user: {user.username}, conv: {conversation.id})"
        )

        return session_data

    async def get_session(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session from Redis.

        Args:
            connection_id: WebSocket connection ID

        Returns:
            Session data dictionary or None if not found
        """
        await self._ensure_redis()

        session_key = self._get_session_key(connection_id)
        session_json = await redis_manager.redis_client.get(session_key)

        if session_json is None:
            logger.warning(f"Session not found: {connection_id}")
            return None

        # Parse and return session data
        session_data = json.loads(session_json)
        return session_data

    async def update_activity(self, connection_id: str):
        """
        Update last activity timestamp for a session.

        Also refreshes the Redis TTL to prevent premature expiration.

        Args:
            connection_id: WebSocket connection ID
        """
        await self._ensure_redis()

        session_key = self._get_session_key(connection_id)

        # Get current session
        session_data = await self.get_session(connection_id)
        if session_data is None:
            return

        # Update last activity
        session_data["last_activity"] = datetime.utcnow().isoformat()

        # Store back with refreshed TTL
        await redis_manager.redis_client.setex(
            session_key,
            SESSION_TTL_SECONDS,
            json.dumps(session_data)
        )

    async def end_session(self, connection_id: str):
        """
        End session and cleanup Redis data.

        Args:
            connection_id: WebSocket connection ID
        """
        await self._ensure_redis()

        session_key = self._get_session_key(connection_id)
        await redis_manager.redis_client.delete(session_key)

        logger.info(f"Ended WebSocket session: {connection_id}")

    # Database helpers (similar to terminal/session.py)

    async def _load_or_create_user(self, session: AsyncSession) -> User:
        """
        Load or create hardcoded user.

        Returns user from database, creates if doesn't exist.
        """
        # Try to find existing user
        result = await session.execute(
            select(User).where(User.username == WEBSOCKET_USER["username"])
        )
        user = result.scalar_one_or_none()

        if user is None:
            # Create new user
            user = User(
                username=WEBSOCKET_USER["username"],
                display_name=WEBSOCKET_USER["display_name"],
                is_active=True,
                preferences={},
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {user.username}")

        return user

    async def _load_character_state(self, session: AsyncSession) -> CharacterState:
        """
        Load default character state.

        Creates default state if doesn't exist.
        """
        # Try to find existing default character state
        result = await session.execute(
            select(CharacterState)
            .order_by(desc(CharacterState.created_at))
            .limit(1)
        )
        character_state = result.scalar_one_or_none()

        if character_state is None:
            # Create default character state
            character_state = CharacterState(
                mood="curious",
                mood_context="Meeting someone new via WebSocket",
                preferences={
                    "conversation_style": "thoughtful",
                    "emoji_usage": "minimal",
                },
                goals={},
            )
            session.add(character_state)
            await session.commit()
            await session.refresh(character_state)
            logger.info("Created default character state")

        return character_state

    async def _load_or_create_conversation(
        self,
        session: AsyncSession,
        user: User,
        character_state: CharacterState,
    ) -> Conversation:
        """
        Load most recent websocket conversation or create new one.

        Args:
            session: Database session
            user: User object
            character_state: CharacterState object

        Returns:
            Conversation with all history loaded
        """
        # Try to find most recent active websocket conversation
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user.id,
                Conversation.platform == "websocket",
                Conversation.ended_at.is_(None),  # Active conversations only
            )
            .order_by(desc(Conversation.started_at))
            .limit(1)
        )
        conversation = result.scalar_one_or_none()

        if conversation is None:
            # Create new conversation
            conversation = Conversation(
                user_id=user.id,
                character_state_id=character_state.id,
                title="WebSocket Conversation",
                platform="websocket",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            logger.info(f"Created new conversation: {conversation.id}")

        return conversation
