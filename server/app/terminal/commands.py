"""
Command handlers for terminal interface.
Implements all slash commands: /help, /exit, /stats, /memories, etc.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.terminal.session import SessionContext, load_or_create_conversation
from app.terminal.display import (
    display_command_help,
    display_system_message,
    display_stats_table,
    display_memories,
    clear_screen,
    display_error,
    display_user_message,
    display_assistant_message,
)
from app.models.conversation import ConversationTurn, MessageRole
from app.llm.inference import get_generation_stats


async def cmd_help() -> None:
    """Show available commands"""
    display_command_help()


async def cmd_exit() -> bool:
    """
    Exit terminal interface.
    Returns False to signal exit from main loop.
    """
    display_system_message("Goodbye!")
    return False


async def cmd_stats(
    session: AsyncSession,
    conversation_id: str,
) -> None:
    """
    Show conversation statistics.
    Uses conversation_history.get_conversation_metadata()
    """
    try:
        # Get stats from inference module
        stats = await get_generation_stats(session, conversation_id)

        # Display with rich table
        display_stats_table(stats)

    except Exception as e:
        display_error(f"Error loading stats: {e}")


async def cmd_memories(
    session_context: SessionContext,
) -> None:
    """
    Show last retrieved memories.
    Displays memories stored in session_context from last generation.
    """
    if session_context.last_retrieved_memories is None:
        display_system_message(
            "No memories retrieved yet. Send a message to see retrieved memories."
        )
        return

    if not session_context.last_retrieved_memories:
        display_system_message("No memories were retrieved for the last query.")
        return

    display_memories(session_context.last_retrieved_memories)


async def cmd_new(
    session: AsyncSession,
    session_context: SessionContext,
) -> None:
    """
    Start new conversation.
    Creates new conversation and updates session_context.
    """
    try:
        # Create new conversation
        new_conversation = await load_or_create_conversation(
            session,
            session_context.user,
            session_context.character_state,
        )

        # Update session context
        session_context.conversation = new_conversation

        # Commit the new conversation
        await session.commit()

        display_system_message(
            f"Started new conversation (ID: {new_conversation.id})"
        )

    except Exception as e:
        display_error(f"Error creating new conversation: {e}")


async def cmd_clear() -> None:
    """Clear screen"""
    clear_screen()


async def cmd_mood(
    session: AsyncSession,
    character_state_id: str,
) -> None:
    """
    Show character state.
    Loads and displays current mood and preferences.
    """
    from app.models.character import CharacterState
    from rich.panel import Panel
    from rich.text import Text
    from app.terminal.display import console

    try:
        # Load character state
        result = await session.execute(
            select(CharacterState).where(CharacterState.id == character_state_id)
        )
        character_state = result.scalar_one_or_none()

        if not character_state:
            display_error("Character state not found")
            return

        # Build display text
        mood_text = Text()
        mood_text.append("Current Mood: ", style="bold white")
        mood_text.append(f"{character_state.mood}\n\n", style="bold green")

        if character_state.mood_context:
            mood_text.append("Context: ", style="bold white")
            mood_text.append(f"{character_state.mood_context}\n\n", style="white")

        if character_state.preferences:
            mood_text.append("Preferences:\n", style="bold white")
            for key, value in character_state.preferences.items():
                mood_text.append(f"  {key}: ", style="cyan")
                mood_text.append(f"{value}\n", style="white")

        # Display in panel
        panel = Panel(
            mood_text,
            title="Eva's Current State",
            border_style="magenta",
        )
        console.print(panel)

    except Exception as e:
        display_error(f"Error loading character state: {e}")


async def cmd_history(
    session: AsyncSession,
    conversation_id: str,
    n_turns: int = 10,
) -> None:
    """
    Show recent conversation history.
    Loads and displays the last N turns.
    """
    from sqlalchemy import desc
    from uuid import UUID

    try:
        # Load recent turns
        result = await session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == UUID(conversation_id))
            .order_by(desc(ConversationTurn.sequence))
            .limit(n_turns)
        )
        turns = list(result.scalars().all())

        if not turns:
            display_system_message("No conversation history yet.")
            return

        # Reverse to show oldest first
        turns.reverse()

        display_system_message(f"Last {len(turns)} turns:")
        print()

        # Display each turn
        for turn in turns:
            if turn.role == MessageRole.USER:
                display_user_message(turn.content)
            elif turn.role == MessageRole.ASSISTANT:
                display_assistant_message(turn.content)
            else:
                display_system_message(f"[System] {turn.content}")

        print()

    except Exception as e:
        display_error(f"Error loading history: {e}")


async def handle_command(
    command: str,
    session_context: SessionContext,
    db_session: AsyncSession,
) -> bool:
    """
    Route command to handler.

    Returns True to continue loop, False to exit.

    Supported commands:
    - /help: Show help
    - /exit, /quit: Exit
    - /stats: Show stats
    - /memories: Show memories
    - /new: New conversation
    - /clear: Clear screen
    - /mood: Show character mood
    - /history [n]: Show history
    """
    # Parse command and arguments
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else None

    # Route to appropriate handler
    if cmd == "/help":
        await cmd_help()
        return True

    elif cmd in ["/exit", "/quit"]:
        return await cmd_exit()

    elif cmd == "/stats":
        await cmd_stats(
            session=db_session,
            conversation_id=str(session_context.conversation.id),
        )
        return True

    elif cmd == "/memories":
        await cmd_memories(session_context)
        return True

    elif cmd == "/new":
        await cmd_new(db_session, session_context)
        return True

    elif cmd == "/clear":
        await cmd_clear()
        return True

    elif cmd == "/mood":
        await cmd_mood(
            session=db_session,
            character_state_id=str(session_context.character_state.id),
        )
        return True

    elif cmd == "/history":
        # Parse optional n_turns argument
        n_turns = 10  # default
        if args:
            try:
                n_turns = int(args)
            except ValueError:
                display_error(f"Invalid number: {args}. Using default (10).")

        await cmd_history(
            session=db_session,
            conversation_id=str(session_context.conversation.id),
            n_turns=n_turns,
        )
        return True

    else:
        display_error(f"Unknown command: {cmd}. Type /help for available commands.")
        return True
