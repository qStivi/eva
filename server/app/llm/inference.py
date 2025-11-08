"""
Memory-Aware LLM Inference

Orchestrates the complete two-track memory system for Eva's responses.
This module ties together all memory components and the LLM to create
context-aware, memory-informed generations.

Key features:
- Orchestrates Track 1 (conversation) and Track 2 (context) integration
- Manages conversation state and memory ingestion
- Handles LLM generation with full memory context
- Provides both synchronous and streaming generation
"""

from typing import Optional, Iterator, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.loader import get_loader
from app.llm.prompts import PromptManager
from app.memory.conversation_track import ConversationHistory
from app.memory.context_track import ContextManager
from app.memory.retrieval import MemoryRetrieval
from app.models.conversation import MessageRole


async def generate_with_memory(
    session: AsyncSession,
    user_id: str,
    conversation_id: str,
    user_message: str,
    character_state_id: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    stream: bool = False,
    save_to_memory: bool = True,
    max_conversation_turns: int = 20,
    max_retrieved_memories: int = 5,
) -> str | Iterator[str]:
    """
    Generate Eva's response with full two-track memory integration.

    This is the main entry point for Phase 3's memory-aware generation.
    It orchestrates the complete pipeline:

    1. Save user message to conversation history (Track 1)
    2. Load recent conversation turns (Track 1)
    3. Search for relevant memories (semantic search)
    4. Build context from memories + preferences + state (Track 2)
    5. Build complete prompt (two-track integration)
    6. Generate response via LLM
    7. Save response to conversation history (Track 1)
    8. Optionally ingest both turns as new memories (Track 2)

    Args:
        session: Database session
        user_id: User ID (UUID as string)
        conversation_id: Conversation ID (UUID as string)
        user_message: The user's message content
        character_state_id: Optional character state ID (UUID as string)
        max_tokens: Maximum tokens to generate (defaults to model config)
        temperature: Sampling temperature (defaults to model config)
        stream: If True, return iterator for streaming generation
        save_to_memory: If True, ingest conversation turns as memories
        max_conversation_turns: Maximum recent turns to include in prompt
        max_retrieved_memories: Maximum memories to retrieve from semantic search

    Returns:
        Generated response string, or Iterator[str] if streaming

    Example:
        >>> response = await generate_with_memory(
        ...     session=db_session,
        ...     user_id="123e4567-e89b-12d3-a456-426614174000",
        ...     conversation_id="456e7890-e89b-12d3-a456-426614174001",
        ...     user_message="What's my favorite food?",
        ...     character_state_id="789e0123-e89b-12d3-a456-426614174002",
        ... )
        >>> print(response)
        "I remember you mentioned loving pizza last week! *flips through notes*"
    """
    # Initialize memory components
    conversation_history = ConversationHistory(max_turns=max_conversation_turns)
    context_manager = ContextManager()
    memory_retrieval = MemoryRetrieval(max_memories=max_retrieved_memories)

    # Get LLM loader
    llm_loader = get_loader()

    # STEP 1: Save user message to conversation history (Track 1)
    user_turn = await conversation_history.save_turn(
        session=session,
        conversation_id=UUID(conversation_id),
        role=MessageRole.USER,
        content=user_message,
    )

    # STEP 2: Load recent conversation history (Track 1)
    turns = await conversation_history.load_history(
        session=session,
        conversation_id=UUID(conversation_id),
        max_turns=max_conversation_turns,
    )

    # Format turns for LLM (exclude system prompt - we'll add it separately)
    conversation_messages = conversation_history.format_for_llm(
        turns=turns,
        system_prompt=None,  # We'll use build_prompt_with_memory instead
    )

    # STEP 3: Search for relevant memories (semantic search via ChromaDB)
    retrieved_memories = await memory_retrieval.search_relevant_memories(
        user_id=user_id,
        query=user_message,
        n_results=max_retrieved_memories,
    )

    # STEP 4: Build context (Track 2)
    context = await context_manager.build_context(
        session=session,
        user_id=user_id,
        character_state_id=character_state_id,
        retrieved_memories=retrieved_memories,
    )

    # STEP 5: Build complete prompt with two-track memory
    prompt = PromptManager.build_prompt_with_memory(
        system_prompt=PromptManager.SYSTEM_PROMPT,
        context=context,
        conversation_history=conversation_messages,
    )

    # STEP 6: Generate response via LLM
    response = llm_loader.generate(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream,
    )

    # Handle streaming vs synchronous generation
    if stream:
        # For streaming, return an async generator that also saves after generation
        return _streaming_with_save(
            response_iterator=response,
            session=session,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            user_turn=user_turn,
            save_to_memory=save_to_memory,
            memory_retrieval=memory_retrieval,
            user_id=user_id,
        )
    else:
        # STEP 7: Save assistant response to conversation history (Track 1)
        assistant_turn = await conversation_history.save_turn(
            session=session,
            conversation_id=UUID(conversation_id),
            role=MessageRole.ASSISTANT,
            content=response,
        )

        # STEP 8: Ingest conversation turns as memories (Track 2)
        if save_to_memory:
            # Ingest user message
            await memory_retrieval.ingest_conversation_turn(
                session=session,
                user_id=user_id,
                conversation_id=conversation_id,
                turn=user_turn,
            )

            # Ingest assistant response
            await memory_retrieval.ingest_conversation_turn(
                session=session,
                user_id=user_id,
                conversation_id=conversation_id,
                turn=assistant_turn,
            )

        return response


async def _streaming_with_save(
    response_iterator: Iterator[str],
    session: AsyncSession,
    conversation_id: str,
    conversation_history: ConversationHistory,
    user_turn,
    save_to_memory: bool,
    memory_retrieval: MemoryRetrieval,
    user_id: str,
) -> Iterator[str]:
    """
    Helper function to handle streaming generation with post-generation saving.

    Yields response chunks and then saves the complete response + memories.

    Args:
        response_iterator: Iterator from LLM streaming generation
        session: Database session
        conversation_id: Conversation ID
        conversation_history: ConversationHistory instance
        user_turn: User's ConversationTurn object
        save_to_memory: Whether to ingest as memories
        memory_retrieval: MemoryRetrieval instance
        user_id: User ID

    Yields:
        Response chunks from LLM
    """
    # Accumulate complete response
    full_response = []

    # Yield chunks as they come
    for chunk in response_iterator:
        full_response.append(chunk)
        yield chunk

    # After streaming is complete, save the response
    complete_response = "".join(full_response)

    # Save assistant response to conversation history
    assistant_turn = await conversation_history.save_turn(
        session=session,
        conversation_id=UUID(conversation_id),
        role=MessageRole.ASSISTANT,
        content=complete_response,
    )

    # Ingest as memories if requested
    if save_to_memory:
        await memory_retrieval.ingest_conversation_turn(
            session=session,
            user_id=user_id,
            conversation_id=conversation_id,
            turn=user_turn,
        )

        await memory_retrieval.ingest_conversation_turn(
            session=session,
            user_id=user_id,
            conversation_id=conversation_id,
            turn=assistant_turn,
        )


async def generate_simple(
    user_message: str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Simple generation without memory (for testing or quick interactions).

    This bypasses the memory system and just does basic LLM generation.
    Useful for testing or one-off interactions.

    Args:
        user_message: The user's message
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated response string

    Example:
        >>> response = await generate_simple("Hello Eva!")
        >>> print(response)
        "Hey! How's it going?"
    """
    llm_loader = get_loader()

    # Create simple prompt
    prompt = PromptManager.create_simple_prompt(user_message)

    # Generate
    response = llm_loader.generate(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False,
    )

    return response


async def get_generation_stats(
    session: AsyncSession,
    conversation_id: str,
) -> Dict[str, Any]:
    """
    Get statistics about a conversation for debugging/monitoring.

    Args:
        session: Database session
        conversation_id: Conversation ID (UUID as string)

    Returns:
        Dict with conversation stats

    Example:
        >>> stats = await get_generation_stats(session, conversation_id)
        >>> print(stats)
        {
            "total_turns": 42,
            "user_turns": 21,
            "assistant_turns": 21,
            "created_at": "2025-11-08T10:00:00",
            "updated_at": "2025-11-08T14:30:00",
        }
    """
    conversation_history = ConversationHistory()

    stats = await conversation_history.get_conversation_metadata(
        session=session,
        conversation_id=UUID(conversation_id),
    )

    return stats
