"""
Terminal session management.
Handles loading/creating user, conversation, and character state.
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.character import CharacterState
from app.models.conversation import Conversation


# Hardcoded user for terminal (single-user design)
TERMINAL_USER = {
    "username": "qStivi",
    "display_name": "Stephan",
}


async def load_or_create_user(session: AsyncSession) -> User:
    """
    Load or create hardcoded user "qStivi" / "Stephan".

    Returns user from database, creates if doesn't exist.
    """
    # Try to find existing user
    result = await session.execute(
        select(User).where(User.username == TERMINAL_USER["username"])
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user
        user = User(
            username=TERMINAL_USER["username"],
            display_name=TERMINAL_USER["display_name"],
            is_active=True,
            preferences={},
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def load_character_state(session: AsyncSession) -> CharacterState:
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
            mood_context="Meeting someone new in terminal",
            preferences={
                "conversation_style": "thoughtful",
                "emoji_usage": "minimal",
            },
            goals={},
        )
        session.add(character_state)
        await session.commit()
        await session.refresh(character_state)

    return character_state


async def load_or_create_conversation(
    session: AsyncSession,
    user: User,
    character_state: CharacterState,
) -> Conversation:
    """
    Load most recent conversation or create new one.

    Returns conversation with all history loaded.
    """
    # Try to find most recent active conversation
    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user.id,
            Conversation.platform == "terminal",
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
            title="Terminal Conversation",
            platform="terminal",
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

    return conversation


@dataclass
class SessionContext:
    """
    Holds session state for terminal interface.

    Attributes:
        user: User object
        character_state: CharacterState object
        conversation: Current conversation
        debug_mode: Whether debug mode is enabled (legacy, enables all)
        debug_memory: Show memory ingestion/retrieval debug output
        debug_prompt: Show prompt assembly debug output
        debug_llm: Show LLM generation debug output
        last_retrieved_memories: Last memories retrieved for /memories command
    """
    user: User
    character_state: CharacterState
    conversation: Conversation
    debug_mode: bool = False
    debug_memory: bool = False
    debug_prompt: bool = False
    debug_llm: bool = False
    last_retrieved_memories: Optional[list] = None


async def initialize_session(
    session: AsyncSession,
    debug: bool = False,
) -> SessionContext:
    """
    Initialize terminal session.

    Loads or creates user, character state, and conversation.
    Returns SessionContext with all loaded data.
    """
    user = await load_or_create_user(session)
    character_state = await load_character_state(session)
    conversation = await load_or_create_conversation(session, user, character_state)

    return SessionContext(
        user=user,
        character_state=character_state,
        conversation=conversation,
        debug_mode=debug,
        debug_memory=debug,  # Enable all debug flags if --debug passed
        debug_prompt=debug,
        debug_llm=debug,
        last_retrieved_memories=None,
    )
