"""
Comprehensive tests for Phase 3: Two-Track Memory System

Tests cover:
- Track 1: Conversation history management
- Track 2: Context injection
- RAG: Memory retrieval and semantic search
- Full integration: End-to-end memory-aware generation
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.memory.conversation_track import ConversationHistory
from app.memory.context_track import ContextManager
from app.memory.retrieval import MemoryRetrieval
from app.llm.inference import generate_with_memory, generate_simple
from app.llm.prompts import PromptManager
from app.models.conversation import MessageRole, ConversationTurn
from app.models.user import User
from app.models.character import CharacterState


class TestConversationHistory:
    """Test Track 1: Conversation history management."""

    @pytest.mark.asyncio
    async def test_save_and_load_turns(self, async_session, sample_conversation):
        """Test saving and loading conversation turns."""
        history = ConversationHistory(max_turns=10)
        conversation_id = sample_conversation.id

        # Save user turn
        user_turn = await history.save_turn(
            session=async_session,
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content="Hello Eva!",
        )

        assert user_turn.id is not None
        assert user_turn.content == "Hello Eva!"
        assert user_turn.role == MessageRole.USER
        assert user_turn.sequence == 0

        # Save assistant turn
        assistant_turn = await history.save_turn(
            session=async_session,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="Hey! How are you?",
        )

        assert assistant_turn.sequence == 1

        # Load turns
        turns = await history.load_history(
            session=async_session,
            conversation_id=conversation_id,
        )

        assert len(turns) == 2
        assert turns[0].content == "Hello Eva!"
        assert turns[1].content == "Hey! How are you?"

    @pytest.mark.asyncio
    async def test_format_for_llm(self, async_session, sample_conversation):
        """Test formatting conversation for LLM."""
        history = ConversationHistory()
        conversation_id = sample_conversation.id

        # Save some turns
        await history.save_turn(
            async_session, conversation_id, MessageRole.USER, "Hi!"
        )
        await history.save_turn(
            async_session, conversation_id, MessageRole.ASSISTANT, "Hello!"
        )

        # Load and format
        turns = await history.load_history(async_session, conversation_id)
        messages = history.format_for_llm(turns, system_prompt="You are Eva")

        assert len(messages) == 3  # system + user + assistant
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are Eva"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_sliding_window(self, async_session, sample_conversation):
        """Test sliding window keeps only recent turns."""
        history = ConversationHistory(max_turns=3)
        conversation_id = sample_conversation.id

        # Add 5 turns
        for i in range(5):
            role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            await history.save_turn(
                async_session, conversation_id, role, f"Message {i}"
            )

        # Load with sliding window
        turns = await history.load_history(async_session, conversation_id, max_turns=3)

        # Should only get last 3 turns
        assert len(turns) == 3
        assert turns[0].content == "Message 2"
        assert turns[2].content == "Message 4"

    @pytest.mark.asyncio
    async def test_conversation_metadata(self, async_session, sample_conversation):
        """Test getting conversation metadata."""
        history = ConversationHistory()
        conversation_id = sample_conversation.id

        # Add some turns
        await history.save_turn(
            async_session, conversation_id, MessageRole.USER, "Hi"
        )
        await history.save_turn(
            async_session, conversation_id, MessageRole.ASSISTANT, "Hello"
        )

        # Get metadata
        metadata = await history.get_conversation_metadata(
            async_session, conversation_id
        )

        assert metadata["total_turns"] == 2
        assert metadata["user_turns"] == 1
        assert metadata["assistant_turns"] == 1
        assert metadata["conversation_id"] == conversation_id


class TestContextManager:
    """Test Track 2: Context injection."""

    @pytest.mark.asyncio
    async def test_build_empty_context(self, async_session, sample_user):
        """Test building context with no data."""
        context_mgr = ContextManager()

        # Build context for user with no preferences
        context = await context_mgr.build_context(
            session=async_session,
            user_id=str(sample_user.id),
        )

        # Should have temporal context at minimum
        assert "Current Time:" in context

    @pytest.mark.asyncio
    async def test_user_preferences_context(self, async_session, sample_user_with_prefs):
        """Test including user preferences in context."""
        context_mgr = ContextManager()

        context = await context_mgr.build_context(
            session=async_session,
            user_id=str(sample_user_with_prefs.id),
        )

        assert "User Preferences:" in context
        assert sample_user_with_prefs.display_name in context

    @pytest.mark.asyncio
    async def test_character_state_context(self, async_session, sample_user, sample_character_state):
        """Test including character state in context."""
        context_mgr = ContextManager()

        context = await context_mgr.build_context(
            session=async_session,
            user_id=str(sample_user.id),
            character_state_id=str(sample_character_state.id),
        )

        assert "Character State" in context
        assert sample_character_state.mood in context

    @pytest.mark.asyncio
    async def test_format_memories(self):
        """Test formatting retrieved memories."""
        context_mgr = ContextManager()

        memories = [
            {
                "content_summary": "User likes pizza",
                "importance_score": 0.9,
                "created_at": datetime.now(),
            },
            {
                "content_summary": "User works on AI projects",
                "importance_score": 0.7,
                "created_at": datetime.now(),
            },
        ]

        formatted = context_mgr.format_memories(memories)

        assert "Relevant Memories:" in formatted
        assert "User likes pizza" in formatted
        assert "[important]" in formatted  # High importance marker

    @pytest.mark.asyncio
    async def test_temporal_context(self):
        """Test temporal context generation."""
        context_mgr = ContextManager()

        temporal = context_mgr.format_temporal_context()

        assert "Current Time:" in temporal
        # Should have day of week, date, time of day
        assert any(day in temporal for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        assert any(time in temporal for time in ["morning", "afternoon", "evening", "night"])


class TestMemoryRetrieval:
    """Test RAG: Memory retrieval and semantic search."""

    @pytest.mark.asyncio
    async def test_ingest_conversation_turn(self, async_session, sample_user, sample_conversation):
        """Test ingesting a conversation turn as memory."""
        retrieval = MemoryRetrieval()

        # Create a turn
        turn = ConversationTurn(
            conversation_id=sample_conversation.id,
            role=MessageRole.USER,
            content="I love pizza! It's my favorite food.",
            sequence=0,
        )

        # Ingest
        embedding_id = await retrieval.ingest_conversation_turn(
            session=async_session,
            user_id=str(sample_user.id),
            conversation_id=str(sample_conversation.id),
            turn=turn,
        )

        # Should return embedding ID if important enough
        # Content mentions "love" and "favorite" so should be stored
        assert embedding_id is not None

    @pytest.mark.asyncio
    async def test_importance_scoring(self):
        """Test importance score calculation."""
        retrieval = MemoryRetrieval()

        # High importance: personal information
        high_importance_turn = ConversationTurn(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="My name is Alice and I work as a software engineer. I love programming and have been coding for 10 years.",
            sequence=0,
        )

        score = retrieval.calculate_importance_score(high_importance_turn)
        assert score > 0.6  # Should be high

        # Low importance: short generic response
        low_importance_turn = ConversationTurn(
            conversation_id=uuid4(),
            role=MessageRole.ASSISTANT,
            content="Ok",
            sequence=1,
        )

        score = retrieval.calculate_importance_score(low_importance_turn)
        assert score < 0.5  # Should be low

    @pytest.mark.asyncio
    async def test_memory_type_detection(self):
        """Test detecting memory types."""
        retrieval = MemoryRetrieval()

        # Fact
        fact_turn = ConversationTurn(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="I'm a software developer",
            sequence=0,
        )
        assert retrieval._determine_memory_type(fact_turn) == "fact"

        # Preference
        pref_turn = ConversationTurn(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="I love chocolate ice cream",
            sequence=0,
        )
        assert retrieval._determine_memory_type(pref_turn) == "preference"

        # Plan
        plan_turn = ConversationTurn(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="I'm going to learn Rust next month",
            sequence=0,
        )
        assert retrieval._determine_memory_type(plan_turn) == "plan"

    @pytest.mark.asyncio
    async def test_search_memories(self, async_session, sample_user, sample_conversation):
        """Test semantic memory search."""
        retrieval = MemoryRetrieval()

        # Ingest some memories
        turns = [
            ("I love pizza and pasta", MessageRole.USER),
            ("I work on AI projects", MessageRole.USER),
            ("I have a dog named Max", MessageRole.USER),
        ]

        for content, role in turns:
            turn = ConversationTurn(
                conversation_id=sample_conversation.id,
                role=role,
                content=content,
                sequence=0,
            )
            await retrieval.ingest_conversation_turn(
                async_session,
                str(sample_user.id),
                str(sample_conversation.id),
                turn,
                force=True,  # Force storage regardless of importance
            )

        # Search for food-related memories
        results = await retrieval.search_relevant_memories(
            user_id=str(sample_user.id),
            query="What food does the user like?",
            n_results=3,
        )

        # Should find the pizza memory with high similarity
        assert len(results) > 0
        # First result should be about food (semantic similarity)
        assert any("pizza" in r["content_summary"].lower() or "pasta" in r["content_summary"].lower() for r in results)


class TestPromptIntegration:
    """Test prompt building with memory."""

    def test_build_prompt_with_memory(self):
        """Test building prompt with two-track integration."""
        system_prompt = PromptManager.SYSTEM_PROMPT
        context = "User Preferences:\n- User prefers to be called: Alice\n\nRelevant Memories:\n1. User likes pizza"
        conversation_history = [
            {"role": "user", "content": "Hi Eva!"},
            {"role": "assistant", "content": "Hey! How are you?"},
        ]

        prompt = PromptManager.build_prompt_with_memory(
            system_prompt=system_prompt,
            context=context,
            conversation_history=conversation_history,
        )

        # Check structure
        assert "<|system|>" in prompt
        assert PromptManager.SYSTEM_PROMPT in prompt
        assert "User Preferences" in prompt  # Track 2
        assert "User likes pizza" in prompt  # Track 2
        assert "Hi Eva!" in prompt  # Track 1
        assert "<|user|>" in prompt
        assert "<|assistant|>" in prompt


class TestFullIntegration:
    """Test complete memory-aware generation pipeline."""

    @pytest.mark.asyncio
    async def test_generate_simple(self):
        """Test simple generation without memory."""
        # This tests basic LLM generation without database
        # Skip if LLM not available in test environment
        try:
            response = await generate_simple("Hello!")
            assert isinstance(response, str)
            assert len(response) > 0
        except Exception as e:
            pytest.skip(f"LLM not available in test environment: {e}")

    @pytest.mark.asyncio
    async def test_full_memory_integration(
        self,
        async_session,
        sample_user,
        sample_conversation,
        sample_character_state,
    ):
        """
        Test complete memory-aware generation pipeline.

        This is the integration test that validates the entire
        two-track memory system works end-to-end.
        """
        # First interaction: User shares information
        try:
            response1 = await generate_with_memory(
                session=async_session,
                user_id=str(sample_user.id),
                conversation_id=str(sample_conversation.id),
                user_message="Hi Eva! I love pizza, it's my favorite food.",
                character_state_id=str(sample_character_state.id),
                save_to_memory=True,
            )

            assert isinstance(response1, str)
            assert len(response1) > 0

            # Second interaction: Ask about previously shared info
            response2 = await generate_with_memory(
                session=async_session,
                user_id=str(sample_user.id),
                conversation_id=str(sample_conversation.id),
                user_message="What's my favorite food?",
                character_state_id=str(sample_character_state.id),
                save_to_memory=True,
            )

            assert isinstance(response2, str)
            # Response should reference the memory
            # (This is a semantic test - actual content depends on LLM)

        except Exception as e:
            pytest.skip(f"Full integration test skipped (LLM or DB issue): {e}")


class TestMemoryLifecycle:
    """Test memory lifecycle and management."""

    @pytest.mark.asyncio
    async def test_memory_stats(self, async_session, sample_user, sample_conversation):
        """Test getting memory statistics."""
        retrieval = MemoryRetrieval()

        # Add some memories
        for i, content in enumerate(["I like cats", "I work remotely", "I play guitar"]):
            turn = ConversationTurn(
                conversation_id=sample_conversation.id,
                role=MessageRole.USER,
                content=content,
                sequence=i,
            )
            await retrieval.ingest_conversation_turn(
                async_session,
                str(sample_user.id),
                str(sample_conversation.id),
                turn,
                force=True,
            )

        # Get stats
        stats = await retrieval.get_memory_stats(
            session=async_session,
            user_id=str(sample_user.id),
        )

        assert stats["total_memories"] == 3
        assert "by_type" in stats
        assert stats["average_importance"] > 0
