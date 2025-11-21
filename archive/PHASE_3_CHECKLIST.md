# Phase 3: Memory System - Two-Track Architecture - Detailed Checklist

**Goal**: Implement the core two-track memory system (conversation + context)
**Estimated Time**: 4-6 hours
**Status**: In Progress (2025-11-08)

---

## Overview

Phase 3 implements Eva's defining feature: the two-track memory architecture.

**Track 1 (Conversation)**: Clean dialogue history - what's actually said
**Track 2 (Context)**: Rich background information - injected separately

This system enables perfect memory without cluttering conversations.

---

## Task 3.1: Memory Module Structure

### 3.1.1 Create Memory Package
**Directory**: `server/app/memory/`

```bash
mkdir -p server/app/memory
touch server/app/memory/__init__.py
```

**Verify**: Module structure exists

---

## Task 3.2: Track 1 - Conversation History

### 3.2.1 Create ConversationHistory Class
**File**: `server/app/memory/conversation_track.py`

**Key Methods**:
- `__init__(max_turns: int)` - Initialize with sliding window size
- `async load_history()` - Load conversation turns from database
- `format_for_llm()` - Format turns for LLM (returns list of dicts)
- `async save_turn()` - Save new turn to database
- `create_sliding_window()` - Keep only recent N turns
- `async get_conversation_metadata()` - Get statistics about conversation

**Verify**:
```python
# Test loading and formatting
history = ConversationHistory(max_turns=10)
turns = await history.load_history(session, conversation_id=1)
messages = history.format_for_llm(turns, system_prompt="You are Eva")
assert messages[0]["role"] == "system"
```

---

## Task 3.3: Track 2 - Context Injection

### 3.3.1 Create ContextManager Class
**File**: `server/app/memory/context_track.py`

**Context Types to Support**:
- Retrieved memories (from semantic search)
- User preferences (from user/character state)
- Current mood/state
- Temporal context (time, date, day of week)
- External triggers (webhooks)

**Key Methods**:
- `async build_context()` - Build complete context string for LLM
- `async get_user_preferences()` - Load user preferences
- `async get_character_state()` - Load character state (mood, etc.)
- `format_temporal_context()` - Generate time/date context
- `format_memories()` - Format retrieved memories for injection
- `format_external_triggers()` - Format webhook triggers

**Verify**:
```python
# Test context building
context_mgr = ContextManager()
context = await context_mgr.build_context(
    session, user_id=1, character_state_id=1,
    retrieved_memories=[{"content": "User likes pizza", "importance": 0.8}]
)
assert "pizza" in context.lower()
```

---

## Task 3.4: RAG Implementation with ChromaDB

### 3.4.1 Create MemoryRetrieval Class
**File**: `server/app/memory/retrieval.py`

**Key Methods**:
- `__init__(min_relevance_score, max_memories)` - Configure retrieval
- `async ingest_conversation_turn()` - Process turn as memory
  1. Analyze if worth remembering
  2. Extract summary
  3. Calculate importance score
  4. Generate embedding via ChromaDB
  5. Store in ChromaDB + PostgreSQL
- `async search_relevant_memories()` - Semantic search for relevant memories
- `calculate_importance_score()` - Score conversation turn importance
- `filter_by_recency()` - Filter to recent memories
- `rank_memories()` - Re-rank by multiple factors

**Verify**:
```python
# Test ingestion and search
retrieval = MemoryRetrieval()
embedding_id = await retrieval.ingest_conversation_turn(
    session, user_id=1, conversation_id=1, turn=turn
)
assert embedding_id is not None

memories = await retrieval.search_relevant_memories(
    user_id=1, query="What food does user like?", n_results=3
)
assert len(memories) <= 3
```

---

## Task 3.5: Memory Integration with LLM

### 3.5.1 Update Prompt System
**File**: `server/app/llm/prompts.py`

Add function:
```python
def build_prompt_with_memory(
    system_prompt: str,
    context: str,
    conversation_history: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Build complete prompt with two-track memory.

    Structure:
    1. System prompt + Context injection (Track 2)
    2. Conversation history (Track 1)
    """
```

### 3.5.2 Create Memory-Aware Generation
**File**: `server/app/llm/inference.py` or similar

```python
async def generate_with_memory(
    session: AsyncSession,
    user_id: int,
    conversation_id: int,
    user_message: str,
    character_state_id: int,
) -> str:
    """
    Generate response with full memory system.

    Process:
    1. Save user message (Track 1)
    2. Load conversation history
    3. Search relevant memories
    4. Build context (Track 2)
    5. Build complete prompt
    6. Generate response
    7. Save response (Track 1)
    8. Ingest turns as memories (Track 2)
    """
```

**Verify**: Test full generation retrieves and uses memories

---

## Task 3.6: Testing

### 3.6.1 Create Memory Tests
**File**: `server/tests/test_memory.py`

Tests to implement:
- `test_conversation_history()` - Test Track 1 (save, load, format)
- `test_context_manager()` - Test Track 2 (context building)
- `test_memory_retrieval()` - Test RAG (ingestion, search)
- `test_full_memory_integration()` - Test complete system

### 3.6.2 Add Test Fixtures
**File**: `server/tests/conftest.py`

Add fixtures:
- `sample_user`
- `sample_character_state`
- `sample_conversation`

**Verify**:
```bash
pytest server/tests/test_memory.py -v
# All tests should pass
```

---

## Task 3.7: Documentation Updates

### 3.7.1 Update IMPLEMENTATION_PLAN.md
- Mark Phase 3 complete
- Add actual time spent
- Note technical decisions

### 3.7.2 Update TIME_LOG.md
- Add Phase 3 time tracking
- Document task durations
- Note any issues encountered

### 3.7.3 Update README.md
- Update current phase to Phase 4

---

## Final Verification Checklist

```bash
# 1. Module structure
ls server/app/memory/
# Should show: __init__.py, conversation_track.py, context_track.py, retrieval.py

# 2. All tests pass
pytest server/tests/test_memory.py -v

# 3. Manual integration test
# Test generate_with_memory function
# Verify memories retrieved and used
```

---

## Git Commit for Phase 3

```bash
git add .
git commit -m "Phase 3 complete: Two-Track Memory System

- Implement Track 1: Conversation history management
- Implement Track 2: Context injection system
- Implement RAG with ChromaDB semantic search
- Integrate memory system with LLM prompts
- Add comprehensive memory tests

Deliverable: Working two-track memory with semantic retrieval"

git push
```

---

## Phase 3 Complete! 🎉

**Deliverables Achieved**:
- ✅ Two-track memory architecture operational
- ✅ Conversation history (Track 1)
- ✅ Context injection (Track 2)
- ✅ Semantic memory retrieval with ChromaDB
- ✅ LLM integration with memory
- ✅ Tests passing

**Ready for Phase 4**: WebSocket Conversation Endpoint
