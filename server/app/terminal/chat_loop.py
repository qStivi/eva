"""
Main chat loop for terminal interface.
Handles user input, command routing, and message processing.
"""
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.terminal.session import initialize_session, SessionContext
from app.terminal.display import (
    display_welcome,
    display_system_message,
    display_error,
    console,
)
from app.terminal.commands import handle_command


async def handle_message(
    user_input: str,
    session_context: SessionContext,
    db_session: AsyncSession,
) -> None:
    """
    Handle user message and generate response.

    1. Display thinking status
    2. Call generate_with_memory()
    3. Stream response with display_streaming_response()
    4. Handle errors
    """
    from app.llm.inference import generate_with_memory
    from app.terminal.display import display_thinking, display_streaming_response, console

    try:
        # Show thinking status
        with display_thinking():
            # Generate response with memory integration
            response_iterator = await generate_with_memory(
                session=db_session,
                user_id=str(session_context.user.id),
                conversation_id=str(session_context.conversation.id),
                user_message=user_input,
                character_state_id=str(session_context.character_state.id),
                stream=True,
            )

        # Convert sync iterator to async iterator for display
        async def async_wrapper():
            for chunk in response_iterator:
                yield chunk

        # Display streaming response
        await display_streaming_response(async_wrapper(), console)

    except Exception as e:
        display_error(f"Error generating response: {e}")
        if session_context.debug_mode:
            raise




async def run_chat_loop(debug: bool = False) -> None:
    """
    Main conversation loop.

    1. Initialize session (user, conversation, character state)
    2. Display welcome
    3. Loop:
       - Prompt for input
       - Detect commands (starts with /)
       - Route to handler
       - Continue until /exit
    4. Graceful shutdown

    Args:
        debug: Enable debug mode
    """
    # Create database session
    async with AsyncSessionLocal() as db_session:
        try:
            # Initialize session context
            if debug:
                display_system_message("Debug mode enabled")

            display_system_message("Initializing session...")
            session_context = await initialize_session(db_session, debug=debug)

            # Display welcome banner
            display_welcome()

            # Create prompt session with history
            prompt_session: PromptSession = PromptSession(
                history=InMemoryHistory(),
                message="You: ",
            )

            # Main conversation loop
            continue_loop = True
            while continue_loop:
                try:
                    # Get user input asynchronously
                    user_input = await prompt_session.prompt_async()

                    # Skip empty input
                    if not user_input or not user_input.strip():
                        continue

                    user_input = user_input.strip()

                    # Check if it's a command
                    if user_input.startswith("/"):
                        continue_loop = await handle_command(
                            user_input,
                            session_context,
                            db_session,
                        )
                    else:
                        # Handle normal message
                        await handle_message(
                            user_input,
                            session_context,
                            db_session,
                        )

                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully
                    console.print()
                    display_system_message("Use /exit or /quit to exit gracefully.")
                    continue

                except EOFError:
                    # Handle Ctrl+D (EOF)
                    console.print()
                    display_system_message("Goodbye!")
                    break

            # Commit any pending changes before exit
            await db_session.commit()
            display_system_message("Session saved. See you next time!")

        except Exception as e:
            display_error(f"An error occurred: {e}")
            if debug:
                raise
