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
from app.llm.api_loader import get_api_loader
from app.llm.prompts import PromptManager
from app.memory.conversation_track import ConversationHistory
from app.memory.context_track import ContextManager
from app.memory.retrieval import MemoryRetrieval
from app.models.conversation import MessageRole
from app.config import settings

# Debug startup test - verify env var loading
import os
import sys
_debug_env = os.getenv("DEBUG", "")
print(f"[STARTUP DEBUG] inference.py loaded | DEBUG env var = '{_debug_env}' | Enabled = {_debug_env.lower() in ('true', '1', 'yes')}")
sys.stdout.flush()


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
    max_conversation_turns: int = 100,  # Increased for API mode (was 20 for local models)
    max_retrieved_memories: int = 5,
    debug_memory: bool = False,
    debug_prompt: bool = False,
    debug_llm: bool = False,
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
        debug_memory: Show memory retrieval debug output
        debug_prompt: Show full prompt structure before generation
        debug_llm: Show LLM generation debug info

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

    # Get LLM loader (API or local based on settings)
    llm_loader = get_api_loader() if settings.use_api else get_loader()

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

    # Debug: Show memory retrieval
    if debug_memory:
        import sys
        print("\n" + "="*80)
        print("DEBUG: MEMORY RETRIEVAL")
        print("="*80)
        print(f"\n[MEMORY SEARCH]")
        print("-" * 40)
        print(f"Query: {user_message[:100]}..." if len(user_message) > 100 else f"Query: {user_message}")
        print(f"Retrieved: {len(retrieved_memories)} memories")
        if retrieved_memories:
            print("\n[RETRIEVED MEMORIES]")
            for i, mem in enumerate(retrieved_memories, 1):
                print(f"\n{i}. (relevance: {mem.get('distance', 'N/A'):.3f})")
                content = mem.get('content_summary', mem.get('content', ''))
                print(f"   {content[:150]}..." if len(content) > 150 else f"   {content}")
        else:
            print("   (No relevant memories found)")
        print("\n" + "="*80 + "\n")
        sys.stdout.flush()

    # STEP 4: Build context (Track 2)
    context = await context_manager.build_context(
        session=session,
        user_id=user_id,
        character_state_id=character_state_id,
        retrieved_memories=retrieved_memories,
    )

    # STEP 5: Build complete prompt with two-track memory
    # For API mode: Don't use tokenizer, return messages directly for OpenAI
    # For local mode: Use tokenizer for proper chat template formatting (fixes special token leakage)
    use_tokenizer = llm_loader.tokenizer if not settings.use_api else None
    prompt = PromptManager.build_prompt_with_memory(
        system_prompt=PromptManager.SYSTEM_PROMPT,
        context=context,
        conversation_history=conversation_messages,
        tokenizer=use_tokenizer,
    )

    # Comprehensive debug output
    import sys
    if debug_prompt:
        print("\n" + "="*80)
        print("DEBUG: FULL LLM PROMPT STRUCTURE")
        print("="*80)

        # Section 1: System Prompt
        print("\n[1] SYSTEM PROMPT:")
        print("-" * 40)
        sys_prompt = PromptManager.SYSTEM_PROMPT
        print(sys_prompt[:500] + ("..." if len(sys_prompt) > 500 else ""))

        # Section 2: Context (Track 2)
        print("\n[2] CONTEXT (Track 2 - Retrieved Memories):")
        print("-" * 40)
        print(f"Memories retrieved: {len(retrieved_memories)}")
        if context:
            print(context[:800] + ("..." if len(context) > 800 else ""))
        else:
            print("(No context)")

        # Section 3: Conversation History (Track 1)
        print("\n[3] CONVERSATION HISTORY (Track 1):")
        print("-" * 40)
        print(f"Total turns: {len(conversation_messages)}")
        for i, msg in enumerate(conversation_messages[-5:], 1):  # Show last 5
            role = msg.get("role", "unknown")
            content_preview = msg.get("content", "")[:100]
            print(f"  Turn {i} [{role}]: {content_preview}..." if len(msg.get("content", "")) > 100 else f"  Turn {i} [{role}]: {content_preview}")

        # Section 4: Generation Parameters
        print("\n[4] GENERATION PARAMETERS:")
        print("-" * 40)
        print(f"  max_tokens: {max_tokens if max_tokens else 'default'}")
        print(f"  temperature: {temperature if temperature else 'default'}")
        print(f"  stream: {stream}")

        # Section 5: Final Prompt Preview
        print("\n[5] FINAL ASSEMBLED PROMPT:")
        print("-" * 40)
        if isinstance(prompt, list):
            # Messages format (API mode)
            print("Format: OpenAI Messages (list of dicts)")
            for i, msg in enumerate(prompt, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                content_preview = content[:200] + "..." if len(content) > 200 else content
                print(f"\nMessage {i} [{role}]:")
                print(f"  {content_preview}")
            # Calculate total length
            total_chars = sum(len(msg.get("content", "")) for msg in prompt)
            print(f"\nTotal prompt length: {total_chars} chars (~{total_chars // 4} tokens)")
        else:
            # String format (local mode)
            print("Format: Chat template string")
            prompt_str = str(prompt)
            print(prompt_str[:2000] + ("..." if len(prompt_str) > 2000 else ""))
            print(f"\nTotal prompt length: {len(prompt_str)} chars (~{len(prompt_str) // 4} tokens)")
        print("\n" + "="*80 + "\n")
        sys.stdout.flush()  # Ensure output appears immediately

    # Debug: Show LLM generation info
    if debug_llm:
        import sys
        print("\n" + "="*80)
        print("DEBUG: LLM GENERATION")
        print("="*80)
        print(f"\n[MODEL INFO]")
        print("-" * 40)
        if settings.use_api:
            print(f"Mode: API")
            print(f"Model: {settings.openai_model}")
            print(f"API Provider: OpenAI")
        else:
            print(f"Mode: Local")
            print(f"Model Path: {settings.model_path}")
            print(f"Context Size: {settings.model_context_size}")
        print(f"\n[GENERATION PARAMETERS]")
        print("-" * 40)
        print(f"max_tokens: {max_tokens if max_tokens else 'default (1024 for API, 256 for local)'}")
        print(f"temperature: {temperature if temperature is not None else 'default (0.7)'}")
        print(f"stream: {stream}")
        print(f"\n[PROMPT STATS]")
        print("-" * 40)
        prompt_str = str(prompt)
        print(f"Total characters: {len(prompt_str)}")
        print(f"Estimated tokens: ~{len(prompt_str) // 4}")  # Rough estimate
        print("\n" + "="*80 + "\n")
        sys.stdout.flush()

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
):
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

    # Yield chunks as they come (response_iterator is sync, not async)
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
    llm_loader = get_api_loader() if settings.use_api else get_loader()

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
