# Eva - Implementation Plan

**Created**: 2025-11-06
**Approach**: Claude Code handles implementation, developer guides and reviews
**Goal**: Build working MVP of character companion with memory and journaling

---

## Overview

This plan breaks the project into 6 phases, each with a testable deliverable. Phases build on each other, so testing between phases is critical.

**Timeline Estimate**: 8-12 weeks for full MVP
**Current Phase**: Phase 6 (Flutter Client)
**Last Updated**: 2025-11-21

**Progress**:
- ✅ Phase 0: Foundation & Infrastructure (Complete: 2025-11-06)
- ✅ Phase 1: Basic LLM Integration (Complete: 2025-11-07)
- ✅ Phase 2: Database Schema & Models (Complete: 2025-11-08)
- ✅ Phase 3: Memory System - Two-Track Architecture (Complete: 2025-11-08)
- ✅ Phase 4: Terminal Interface (Complete: 2025-11-21)
  - **Bonus**: OpenAI API integration (testing until new GPU)
  - **Bonus**: Eva tsundere fox character personality
  - **Bonus**: Advanced debug system (memory/prompt/llm modes)
  - **Bonus**: Increased history (100 turns), max_tokens (1024)
- ✅ Phase 5: WebSocket Conversation Endpoint (Complete: 2025-11-21)
  - Real-time conversation with streaming responses
  - Redis-backed session management
  - Message protocol with Pydantic validation
- ⏳ Phase 6: Flutter Client (Next)

---

## Phase 0: Foundation & Infrastructure (Week 1)

**Goal**: Set up project structure, databases, and basic configuration

### Tasks

#### 0.1 Project Structure Setup
- [ ] Create `.gitignore` for Python, Flutter, databases, and models
- [ ] Initialize git repository with initial commit
- [ ] Create GitHub/GitLab repository and push
- [ ] Set up branch protection (work on feature branches)

#### 0.2 Server Foundation
- [ ] Create `server/app/__init__.py` (package initialization)
- [ ] Create `server/app/config.py` (configuration management with pydantic-settings)
- [ ] Create `server/app/main.py` (FastAPI application entry point)
- [ ] Add health check endpoint (`GET /health`)
- [ ] Add CORS middleware for development
- [ ] Set up logging configuration

#### 0.3 Environment Configuration
- [ ] Create `server/.env.example` with all required variables:
  - Database URLs (PostgreSQL, Redis, ChromaDB)
  - Model configuration
  - Character settings
  - Feature flags (voice enabled, etc.)
- [ ] Create `server/.env` (from example, add to .gitignore)
- [ ] Add python-dotenv loading in config.py

#### 0.4 Database Setup
- [ ] Update `docker-compose.yml` with proper service configuration
- [ ] Add volume mounts for persistence
- [ ] Add health checks for each service
- [ ] Create database initialization scripts
- [ ] Start databases: `docker-compose up -d`
- [ ] Verify all services are running

#### 0.5 Python Virtual Environment
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Update `requirements.txt` with pinned versions
- [ ] Add development dependencies (pytest, black, ruff, etc.)
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Verify FastAPI starts: `uvicorn app.main:app --reload`

#### 0.6 Testing Framework
- [ ] Create `server/tests/conftest.py` (pytest fixtures)
- [ ] Create `server/tests/test_health.py` (first test)
- [ ] Set up pytest configuration in `pyproject.toml`
- [ ] Run tests to verify setup: `pytest`

**Deliverable**: Running FastAPI server with health endpoint, all databases operational, tests passing

**Testing Checkpoint**:
```bash
# Server starts without errors
cd server && uvicorn app.main:app --reload

# Databases are accessible
docker-compose ps  # All services "Up"
psql -h localhost -U user -d character_companion -c "SELECT 1;"
redis-cli ping  # Returns PONG
curl http://localhost:8000  # ChromaDB health check

# Tests pass
pytest
```

---

## Phase 1: Basic LLM Integration (Week 2) ✅ COMPLETE

**Goal**: Get LLM responding to basic prompts via API endpoint

**Status**: ✅ Complete (2025-11-07)
**Time**: ~2.5 hours actual vs 3-4 hours estimated

### Tasks

#### 1.1 LLM Module Structure
- [x] Create `server/app/llm/__init__.py`
- [x] Create `server/app/llm/config.py` (model configuration)
- [x] Create `server/app/llm/loader.py` (model loading - **using transformers library**, see Technical Decision below)
- [x] Create `server/app/llm/prompts.py` (prompt templates for Eva character)

**Technical Decision (2025-11-07)**: Using `transformers` library instead of `llama-cpp-python`
- Original plan: llama-cpp-python (requires C++ compiler on Windows)
- Attempted: ctransformers (failed to load Phi-3 model)
- Final choice: transformers (documented fallback option, better for development)
- See TIME_LOG.md for detailed reasoning

#### 1.2 Model Loading
- [x] Implement model loader with lazy initialization
- [x] Add model configuration (context size, threads, temperature)
- [x] Download model (microsoft/Phi-3-mini-4k-instruct from HuggingFace)
- [x] Test model loading and inference in isolation
- [x] Add error handling for missing/invalid models

#### 1.3 Character Prompt System
- [x] Design Eva's base system prompt (character-first language)
- [x] Create prompt template with context injection points
- [x] Implement prompt formatting function
- [x] Add conversation history formatting
- [x] Test prompts generate character-appropriate responses

#### 1.4 Simple Generation Endpoint
- [x] Create `server/app/routes/generate.py`
- [x] Implement `POST /api/generate` endpoint (simple completion)
- [x] Accept: prompt text, optional parameters
- [x] Return: generated text, metadata (tokens, time)
- [x] Add request/response models with Pydantic
- [x] Test endpoint with curl

#### 1.5 Testing
- [x] Test model loading with transformers
- [x] Test character prompt formatting
- [x] Test generation endpoint with curl
- [x] Verify character-appropriate responses
- [x] Document critical fix: `attn_implementation="eager"`

**Deliverable**: API endpoint that generates responses using local LLM with Eva's character

**Testing Checkpoint**:
```bash
# Test generation endpoint
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello Eva, how are you?", "max_tokens": 100}'

# Should return character-appropriate response
# Example: "Hey! I'm doing pretty well, thanks for asking..."
```

---

## Phase 2: Database Schema & Models (Week 3) ✅ COMPLETE

**Goal**: Set up database schemas and ORM models for conversations and memory

**Status**: ✅ Complete (2025-11-08)
**Time**: ~2 hours actual vs 3-4 hours estimated

### Tasks

#### 2.1 SQLAlchemy Setup
- [x] Create `server/app/database.py` (async SQLAlchemy configuration)
- [x] Add async session support (SQLAlchemy 2.0 async with asyncpg)
- [x] Implement session dependency for FastAPI routes
- [x] Create Base class for models

#### 2.2 Database Models
- [x] Create `server/app/models/` package with individual model files:
  - `user.py` - User accounts with preferences (multi-user support)
  - `conversation.py` - Conversation sessions and ConversationTurn (Track 1)
  - `memory.py` - Memories with ChromaDB embedding links (Track 2)
  - `journal.py` - JournalEntry with Logseq integration
  - `character.py` - CharacterState (mood, preferences, goals)

#### 2.3 PostgreSQL Schema Migration
- [x] Set up Alembic for async migrations
- [x] Configure alembic.ini and env.py for async SQLAlchemy
- [x] Create initial migration script (47b095bb69b7)
- [x] Run migration: `alembic upgrade head`
- [x] Add indexes for common queries (user_id, conversation_id, created_at, etc.)
- [x] Add foreign key constraints with CASCADE delete
- [x] Fix CharacterState.updated_at nullable (migration 953f735935ef)

#### 2.4 Redis Session Manager
- [x] Create `server/app/redis_manager.py`
- [x] Implement session storage (conversation state with TTL)
- [x] Add active conversation tracking
- [x] Create caching layer with pattern invalidation
- [x] Test Redis connection in init_db.py

#### 2.5 ChromaDB Setup
- [x] Create `server/app/chroma_manager.py`
- [x] Initialize per-user collections (`user_{id}_memories`)
- [x] Configure embedding function (sentence-transformers/all-MiniLM-L6-v2)
- [x] Implement add/search/update/delete operations
- [x] Test vector search with metadata filtering

#### 2.6 Testing & Initialization
- [x] Create `server/init_db.py` for database initialization
- [x] Test database connections (PostgreSQL, Redis, ChromaDB)
- [x] Create default user and character state
- [x] Verify all systems operational

**Deliverable**: Complete database layer with models, migrations, Redis/ChromaDB managers, all tested and operational

**Testing Checkpoint**:
```bash
# Run database initialization and tests
cd server && python init_db.py

# Expected output:
# ✓ Database initialization complete!
# ✓ Redis connection successful
# ✓ ChromaDB connection successful

# Verify migrations
alembic current
# Should show: 953f735935ef (head)

# Verify tables created
psql -h localhost -U user -d character_companion -c "\dt"
# Should list: users, character_states, conversations, conversation_turns, memories, journal_entries
```

---

## Phase 3: Memory System - Two-Track Architecture (Week 4) ✅ COMPLETE

**Goal**: Implement the core two-track memory system (conversation + context)

**Status**: ✅ Complete (2025-11-08)
**Time**: ~2.5 hours actual vs 4-6 hours estimated

### Tasks

#### 3.1 Memory Module Structure
- [x] Create `server/app/memory/__init__.py` (already existed)
- [x] Create `server/app/memory/conversation_track.py` (Track 1) - already implemented
- [x] Create `server/app/memory/context_track.py` (Track 2)
- [x] Create `server/app/memory/retrieval.py` (RAG implementation)

#### 3.2 Track 1: Conversation History
- [x] Implement conversation history manager (ConversationHistory class)
- [x] Store clean user/assistant messages
- [x] Format history for LLM context window
- [x] Implement sliding window (keep recent N turns)
- [x] Add conversation metadata retrieval
- [x] Save to PostgreSQL after each turn

#### 3.3 Track 2: Context Injection
- [x] Implement context manager (ContextManager class)
- [x] Store metadata separately from conversation
- [x] Design context injection format for LLM
- [x] Support multiple context types:
  - [x] Retrieved memories
  - [x] User preferences
  - [x] Current mood/state
  - [x] Temporal context (time, date)
  - [x] External triggers (webhooks - structure ready for Phase 5+)

#### 3.4 RAG Implementation with ChromaDB
- [x] Implement embedding generation (sentence-transformers via ChromaManager)
- [x] Create memory ingestion pipeline:
  - [x] Take conversation turn
  - [x] Extract meaningful segments
  - [x] Generate embeddings
  - [x] Store in ChromaDB with metadata
- [x] Implement semantic search:
  - [x] Query based on current message
  - [x] Retrieve top K relevant memories
  - [x] Filter by recency, relevance, importance
- [x] Add memory importance scoring
- [x] Add memory type detection (fact, preference, plan, event)

#### 3.5 Memory Integration with LLM
- [x] Update prompt system to include both tracks (build_prompt_with_memory)
- [x] Format: System prompt + Context + Conversation history
- [x] Ensure context doesn't pollute conversation
- [x] Create generate_with_memory() orchestration function
- [x] Add streaming support with memory ingestion

#### 3.6 Testing
- [x] Create `server/tests/test_memory.py` (comprehensive test suite)
- [x] Test conversation history management
- [x] Test context injection formatting
- [x] Test RAG retrieval accuracy
- [x] Test importance scoring and memory type detection
- [x] Update conftest.py with async fixtures

**Deliverable**: Working two-track memory system with semantic retrieval

**Testing Checkpoint**:
```python
# Simulate multi-turn conversation
# Turn 1
response1 = generate_with_memory("I love pizza")
# Should store "user likes pizza" in memory

# Turn 2 (later session)
response2 = generate_with_memory("What should I eat?")
# Should retrieve "user likes pizza" and suggest pizza
# Context injected silently, not visible in conversation
```

---

## Phase 4: Terminal Interface (Week 5) ✅ COMPLETE

**Goal**: Interactive terminal interface for testing and single-user conversations

**Status**: ✅ Complete (2025-11-21)
**Time**: ~3 sessions over 2 weeks (Phase 4 baseline + API integration + debug improvements)

**Decision**: Changed from WebSocket to Terminal Interface to validate Phases 0-3 in production-like environment before adding network complexity. WebSocket moved to Phase 5.

**Rationale**:
- Test memory system works correctly before adding WebSocket layer
- Easier debugging without network protocol
- Perfect for single-user (qStivi/Stephan) personal use
- Foundation for all other interfaces

### Tasks

#### 4.1 Setup & Dependencies
- [x] Add `prompt-toolkit>=3.0.52` to requirements.txt
- [x] Add `rich>=14.1.0` to requirements.txt
- [x] Install dependencies: `pip install -r requirements.txt`
- [x] Create `server/app/terminal/` package
- [x] Create `__init__.py`, `main.py`, `chat_loop.py`, `commands.py`, `display.py`, `session.py`

#### 4.2 Session Management
- [x] Create `server/app/terminal/session.py`
- [x] Implement `load_or_create_user()` - hardcoded "qStivi" / "Stephan"
- [x] Create user on first run if doesn't exist
- [x] Implement `load_or_create_conversation()`
- [x] Load character state from database
- [x] Track active conversation_id in session context

#### 4.3 Display Utilities
- [x] Create `server/app/terminal/display.py`
- [x] Implement `display_user_message()` - cyan color
- [x] Implement `display_assistant_message()` - green bold color
- [x] Implement `display_system_message()` - yellow dim
- [x] Implement `display_streaming_response()` - rich.Live integration
- [x] Implement `display_welcome()` - banner with rich.Panel
- [x] Implement `display_stats_table()` - rich.Table for /stats
- [x] Implement `display_memories()` - format retrieved memories

#### 4.4 Basic Chat Loop
- [x] Create `server/app/terminal/chat_loop.py`
- [x] Initialize prompt_toolkit PromptSession
- [x] Display welcome banner
- [x] Implement main conversation loop:
  - Prompt for input with `prompt_async()`
  - Detect commands (starts with /)
  - Route to command handler or message handler
  - Continue until /exit
- [x] Handle Ctrl+C gracefully
- [x] Commit database changes on shutdown

#### 4.5 Message Handler
- [x] In `chat_loop.py`, create `handle_message()`
- [x] Call `generate_with_memory()` with streaming=True
- [x] Display "Eva is thinking..." with rich.Status
- [x] Stream response chunks with `display_streaming_response()`
- [x] Handle errors gracefully (LLM timeout, database errors)
- [x] Add blank line after response for readability

#### 4.6 Command System
- [x] Create `server/app/terminal/commands.py`
- [x] Implement `/help` - Show available commands with descriptions
- [x] Implement `/exit` or `/quit` - Exit gracefully
- [x] Implement `/stats` - Show conversation statistics (turn count, timestamps)
- [x] Implement `/memories` - Show retrieved memories for last message
- [x] Implement `/new` - Start new conversation
- [x] Implement `/clear` - Clear screen (keep conversation in DB)
- [x] Implement `/mood` - Show character state (mood, preferences)
- [x] Implement `/history` - Show recent conversation turns
- [x] Optional: `/debug` - Toggle debug mode (show context lengths, prompts)

#### 4.7 Main Entry Point
- [x] Create `server/app/terminal/main.py`
- [x] Add argument parser (argparse)
- [x] Add `--debug` flag for debug mode
- [x] Initialize database connection
- [x] Call chat_loop with asyncio.run()
- [x] Handle initialization errors (database not running, etc.)

#### 4.8 Testing & Polish
- [x] Test multi-turn conversations
- [x] Verify memory retrieval with `/memories` command
- [x] Test all commands work correctly
- [x] Test conversation persistence (exit and resume)
- [x] Test error handling (empty input, database errors)
- [x] Test on Windows terminal
- [x] Verify streaming response displays smoothly
- [x] Test command history (up/down arrows)

#### 4.9 Documentation
- [x] Update TIME_LOG.md with Phase 4 entry
- [x] Update IMPLEMENTATION_PLAN.md with Phase 4 completion
- [ ] Create `docs/TERMINAL_USAGE.md` (optional usage guide - deferred)

**Deliverable**: Working terminal interface with full memory integration and debugging commands

**Testing Checkpoint**:
```bash
# Start terminal interface
cd server && python -m app.terminal.main

# Test conversation
You: Hello Eva!
Eva: Hey! How's it going? *smiles*

# Test memory
You: I love pizza
Eva: Nice! I'll remember that. *jots down notes*

You: /memories
╭─ Retrieved Memories ─────────╮
│ No memories yet (first chat!) │
╰───────────────────────────────╯

# Test stats
You: /stats
╭─ Conversation Statistics ────╮
│ Total Turns:      4          │
│ User Turns:       2          │
│ Assistant Turns:  2          │
╰───────────────────────────────╯

# Test resume
You: /exit
Eva: See you later! *waves*

# Restart and resume
python -m app.terminal.main
You: What food do I like?
Eva: I remember you mentioned loving pizza!
```

---

## Phase 5: WebSocket Conversation Endpoint (Week 6) ✅ COMPLETE

**Goal**: Real-time conversation via WebSocket with streaming responses

**Status**: ✅ Complete (2025-11-21)
**Time**: ~6 hours (implementation + testing + fixes)

### Tasks

#### 5.1 WebSocket Infrastructure
- [x] Create `server/app/routes/conversation.py`
- [x] Implement `WS /ws/conversation` endpoint
- [x] Add WebSocket connection manager (`server/app/websocket/connection_manager.py`)
- [x] Handle connection lifecycle (connect, disconnect, errors)
- [x] Implement authentication (token-based using SECRET_KEY)

#### 5.2 Message Protocol
- [x] Design WebSocket message format (JSON):
  - Client → Server: `{type: "message", content: "...", metadata: {...}}`
  - Server → Client: `{type: "response_chunk", content: "...", done: false/true}`
  - Server → Client: `{type: "error", code: "...", message: "...", recoverable: true/false}`
  - Server → Client: `{type: "system", event: "...", data: {...}}`
- [x] Implement message validation with Pydantic (`server/app/websocket/message_protocol.py`)
- [x] Add message type handlers

#### 5.3 Streaming Response Implementation
- [x] Integrate LLM streaming (reused `generate_with_memory` from terminal)
- [x] Stream tokens via WebSocket as generated
- [x] Send "done" signal when complete
- [x] Handle stream interruption/cancellation
- [x] Add system event notifications (thinking, retrieving memories)

#### 5.4 Conversation Session Management
- [x] Create or resume conversation session
- [x] Load conversation history from database
- [x] Retrieve relevant memories from ChromaDB
- [x] Update session state in Redis (`server/app/websocket/session_manager.py`)
- [x] Save each turn to PostgreSQL
- [x] Auto-cleanup with TTL (1 hour)

#### 5.5 Integration
- [x] Connect WebSocket handler to memory system
- [x] Connect to LLM generation with streaming
- [x] Implement full conversation loop:
  1. Receive user message
  2. Load conversation history (Track 1)
  3. Retrieve relevant memories (Track 2)
  4. Format prompt with both tracks
  5. Generate response with streaming
  6. Save turn to database
  7. Update memory embeddings
- [x] Add error handling and recovery (sanitized errors, no stack traces)

#### 5.6 Testing
- [x] Create test client (`server/test_websocket_client.py`)
- [x] Test WebSocket connection
- [x] Test message sending/receiving
- [x] Test streaming responses (45 chunks, 7.4s generation)
- [x] Test conversation persistence
- [x] Test memory retrieval during conversation

**Deliverable**: Full WebSocket conversation endpoint with memory and streaming

**Key Implementation Details**:
- **Authentication**: Simple token-based (SECRET_KEY from config) - sufficient for MVP
- **Message Protocol**: Pydantic models for validation, structured JSON messages
- **Session Management**: Redis-backed with 1-hour TTL for auto-cleanup
- **Error Handling**: All errors sanitized before sending to client (security best practice)
- **Streaming**: Reuses existing `generate_with_memory` infrastructure from terminal
- **Platform**: `websocket` platform type distinguishes from terminal conversations

**Testing Checkpoint**:
```bash
# Use websocat or similar tool
websocat ws://localhost:8080/ws/conversation?token=test

# Send message
{"type": "message", "content": "Hi Eva!"}

# Should receive streaming response
{"type": "response", "content": "Hey", "done": false}
{"type": "response", "content": "!", "done": false}
{"type": "response", "content": " How", "done": false}
...
{"type": "response", "content": "", "done": true}
```

---

## Phase 6: Flutter Client - Basic UI (Week 7-8)

**Goal**: Cross-platform Flutter app with text chat interface

### Tasks

#### 5.1 Flutter Project Setup
- [ ] Initialize Flutter project: `flutter create client`
- [ ] Configure for multi-platform (iOS, Android, Desktop, Web)
- [ ] Set up project structure:
  - `/lib/main.dart` - Entry point
  - `/lib/config/` - Configuration
  - `/lib/models/` - Data models
  - `/lib/services/` - API clients
  - `/lib/screens/` - UI screens
  - `/lib/widgets/` - Reusable widgets
  - `/lib/providers/` - State management (Riverpod or Provider)

#### 5.2 Dependencies
- [ ] Add to `pubspec.yaml`:
  - `web_socket_channel` - WebSocket client
  - `http` - HTTP requests
  - `provider` or `riverpod` - State management
  - `shared_preferences` - Local storage
  - `flutter_markdown` - Markdown rendering
  - `intl` - Internationalization
- [ ] Run `flutter pub get`

#### 5.3 WebSocket Service
- [ ] Create `lib/services/websocket_service.dart`
- [ ] Implement WebSocket connection manager
- [ ] Handle connection states (connecting, connected, disconnected, error)
- [ ] Parse incoming messages (streaming, errors)
- [ ] Send messages with proper formatting
- [ ] Add reconnection logic

#### 5.4 Data Models
- [ ] Create `lib/models/message.dart` (user/assistant message)
- [ ] Create `lib/models/conversation.dart` (conversation metadata)
- [ ] Create `lib/models/character.dart` (character info)
- [ ] Add JSON serialization

#### 5.5 State Management
- [ ] Create `lib/providers/conversation_provider.dart`
- [ ] Manage conversation state (messages, loading, errors)
- [ ] Handle WebSocket connection state
- [ ] Implement message sending/receiving
- [ ] Add optimistic updates (show user message immediately)

#### 5.6 Chat Screen UI
- [ ] Create `lib/screens/chat_screen.dart`
- [ ] Implement message list view (scrollable)
- [ ] Create message bubble widget (user vs assistant styling)
- [ ] Add text input field with send button
- [ ] Show typing indicator during response generation
- [ ] Add timestamps
- [ ] Implement auto-scroll to latest message

#### 5.7 Polish & UX
- [ ] Add loading states
- [ ] Add error handling and display
- [ ] Implement offline message queueing
- [ ] Add pull-to-refresh for conversation history
- [ ] Create settings screen (server URL, etc.)
- [ ] Add app icon and splash screen

#### 5.8 Testing
- [ ] Widget tests for UI components
- [ ] Integration tests for WebSocket connection
- [ ] Test on multiple platforms (iOS, Android, Desktop)

**Deliverable**: Working Flutter app with text chat, connects to server via WebSocket

**Testing Checkpoint**:
```bash
# Run on desktop for quick testing
cd client && flutter run -d windows

# Test flow:
1. App opens to chat screen
2. Type "Hi Eva!" and send
3. Should see message appear immediately
4. Should see typing indicator
5. Should receive streaming response
6. Response should accumulate in message bubble
7. Conversation should persist on restart
```

---

## Phase 6: Journal Integration - Logseq (Week 8)

**Goal**: Read existing journal, write new entries in user's style

### Tasks

#### 6.1 Journal Module Structure
- [ ] Create `server/app/journal/__init__.py`
- [ ] Create `server/app/journal/logseq_parser.py`
- [ ] Create `server/app/journal/writer.py`
- [ ] Create `server/app/journal/style_analyzer.py`

#### 6.2 Logseq Parser
- [ ] Implement Markdown file reader
- [ ] Parse Logseq format (bullets, tags, links)
- [ ] Extract journal entries by date
- [ ] Parse metadata (properties, tags)
- [ ] Handle page links and block references
- [ ] Build entry structure (hierarchy, relationships)

#### 6.3 Writing Style Analysis
- [ ] Analyze user's existing journal entries
- [ ] Extract style patterns:
  - Average entry length
  - Common phrases and vocabulary
  - Bullet structure and nesting
  - Emoji usage
  - Tag frequency
  - Tone (formal, casual, etc.)
- [ ] Create style profile for user
- [ ] Store in database or config

#### 6.4 Journal Entry Generation
- [ ] Design journal extraction prompt for LLM
- [ ] Feed conversation into prompt with style guide
- [ ] Generate entry in user's style
- [ ] Format as Logseq-compatible Markdown
- [ ] Add appropriate tags and links
- [ ] Include timestamp and metadata

#### 6.5 Safe File Writing
- [ ] Implement atomic file writes (write to temp, then move)
- [ ] Add file locking to prevent conflicts
- [ ] Create backup before writing
- [ ] Validate Markdown syntax
- [ ] Handle write errors gracefully

#### 6.6 Journal API Endpoints
- [ ] Create `server/app/routes/journal.py`
- [ ] `GET /api/journal/entries` - List journal entries
- [ ] `POST /api/journal/generate` - Generate entry from conversation
- [ ] `GET /api/journal/style` - Get user's writing style profile

#### 6.7 Background Processing
- [ ] Implement background task queue (or simple async)
- [ ] Auto-generate journal entries after conversations
- [ ] Add user preference: manual or automatic journaling
- [ ] Send notification when entry is ready

#### 6.8 Flutter Integration
- [ ] Create `lib/screens/journal_screen.dart`
- [ ] Display recent journal entries
- [ ] Show journal generation status
- [ ] Add "Generate journal entry" button
- [ ] Render Markdown with preview

#### 6.9 Testing
- [ ] Create `server/tests/test_logseq_parser.py`
- [ ] Create `server/tests/test_journal_generation.py`
- [ ] Test with sample Logseq journals
- [ ] Verify style matching
- [ ] Test safe file writing

**Deliverable**: System reads existing journal, generates new entries in user's style

**Testing Checkpoint**:
```bash
# Point system at test Logseq directory
# Have a conversation
# Generate journal entry
POST /api/journal/generate {"conversation_id": 123}

# Check output:
1. Entry written to Logseq directory
2. Format matches user's style
3. Tags and links added appropriately
4. Conversation content summarized naturally
5. Written from character's perspective (character-first)
```

---

## Phase 7: Character Features - Mood & Preferences (Week 9)

**Goal**: Add basic mood system and preference learning

### Tasks

#### 7.1 Character State System
- [ ] Extend `CharacterState` database model
- [ ] Add mood tracking (happy, neutral, contemplative, concerned, etc.)
- [ ] Add preference storage (key-value pairs)
- [ ] Track user patterns (conversation times, topics, etc.)

#### 7.2 Mood System
- [ ] Implement mood state machine
- [ ] Moods affected by:
  - Conversation content (positive/negative)
  - Time since last interaction
  - User's emotional state (detected)
  - Length of conversation
- [ ] Mood influences:
  - Response tone
  - Initiative level
  - Emoji usage
  - Verbosity
- [ ] Persist mood across sessions

#### 7.3 Preference Learning
- [ ] Detect patterns in conversations:
  - User interests
  - Communication style preferences
  - Time preferences
  - Topic preferences
- [ ] Store preferences with confidence scores
- [ ] Use preferences to:
  - Personalize responses
  - Suggest relevant topics
  - Adjust conversation style

#### 7.4 Character Initiative
- [ ] Implement trigger system:
  - Time-based (morning greeting, goodnight)
  - Event-based (long absence, important date)
  - Context-based (user seems stressed)
- [ ] Character can start conversations
- [ ] Send proactive messages via notifications

#### 7.5 Integration
- [ ] Add mood to prompt context
- [ ] Include preferences in context injection
- [ ] Update WebSocket to expose character state
- [ ] Add initiative triggers to background tasks

#### 7.6 Flutter UI Updates
- [ ] Display character mood indicator (emoji, color, etc.)
- [ ] Show character preferences in settings
- [ ] Support push notifications for initiative
- [ ] Add "About Eva" screen showing learned preferences

#### 7.7 Testing
- [ ] Test mood transitions
- [ ] Test preference learning accuracy
- [ ] Test initiative trigger conditions

**Deliverable**: Character with persistent mood, learned preferences, and basic initiative

---

## Phase 8: Webhook System & External Integrations (Week 10)

**Goal**: Accept triggers from external systems (Home Assistant, IFTTT, etc.)

### Tasks

#### 8.1 Webhook Endpoint
- [ ] Create `server/app/routes/webhook.py`
- [ ] Implement `POST /api/webhook/trigger`
- [ ] Accept generic webhook payload:
  - `trigger_type` (automation, calendar, custom)
  - `user_id`
  - `context` (event details)
  - `suggested_prompt` (optional)
- [ ] Validate webhook signature (HMAC)
- [ ] Queue webhook for processing

#### 8.2 Trigger Processing
- [ ] Parse webhook payload
- [ ] Add context to character's memory
- [ ] Determine if immediate response needed
- [ ] Generate proactive message if appropriate
- [ ] Store trigger in database for history

#### 8.3 Integration Examples
- [ ] Document Home Assistant integration
- [ ] Document IFTTT integration
- [ ] Create example automation configs
- [ ] Test with real webhook payloads

#### 8.4 Testing
- [ ] Test webhook authentication
- [ ] Test various trigger types
- [ ] Test context enrichment

**Deliverable**: Working webhook system accepting external triggers

---

## Phase 9: Polish, Testing & Deployment (Week 11-12)

**Goal**: Production-ready system with deployment scripts

### Tasks

#### 9.1 Comprehensive Testing
- [ ] Write integration tests for full conversation flow
- [ ] Test multi-user support
- [ ] Load testing (concurrent conversations)
- [ ] Test error recovery
- [ ] Test data persistence and migration

#### 9.2 Error Handling & Logging
- [ ] Comprehensive error handling in all modules
- [ ] Structured logging (JSON format)
- [ ] Log aggregation setup
- [ ] Add error reporting (sentry or similar)
- [ ] Graceful degradation (e.g., disable voice if unavailable)

#### 9.3 Configuration & Documentation
- [ ] Document all environment variables
- [ ] Create deployment guide
- [ ] API documentation (OpenAPI/Swagger)
- [ ] User guide for Flutter app
- [ ] Create sample configurations

#### 9.4 Performance Optimization
- [ ] Profile LLM inference time
- [ ] Optimize database queries
- [ ] Implement caching where appropriate
- [ ] Reduce memory footprint
- [ ] Test with realistic data volume

#### 9.5 Deployment Scripts
- [ ] Create systemd service files
- [ ] Create installation script
- [ ] Set up Nginx reverse proxy
- [ ] Configure SSL/TLS
- [ ] Add monitoring (health checks, metrics)

#### 9.6 Security Audit
- [ ] Review authentication implementation
- [ ] Check for SQL injection vulnerabilities
- [ ] Validate WebSocket security
- [ ] Review file permissions (Logseq directory)
- [ ] Add rate limiting

**Deliverable**: Production-ready system with deployment scripts and documentation

---

## Phase 10: Repository Polish & GitHub Setup (Final Week)

**Goal**: Clean up repository, add documentation, configure GitHub features

### Tasks

#### 10.1 GitHub Repository Setup
- [ ] Add comprehensive README.md with:
  - Project overview and vision
  - Quick start guide
  - Installation instructions
  - Architecture diagram
  - Screenshots/demo
- [ ] Create CONTRIBUTING.md guidelines
- [ ] Add LICENSE file (choose appropriate license)
- [ ] Create .github/ISSUE_TEMPLATE/ for bug reports and features
- [ ] Create .github/PULL_REQUEST_TEMPLATE.md
- [ ] Set up GitHub Actions CI/CD:
  - Run tests on push
  - Code quality checks (black, ruff)
  - Build validation
- [ ] Add repository topics/tags for discoverability
- [ ] Enable GitHub Discussions for community

#### 10.2 Documentation Polish
- [ ] Add docstrings to all public functions
- [ ] Generate API documentation (Sphinx or MkDocs)
- [ ] Create deployment guide
- [ ] Add troubleshooting guide
- [ ] Document environment variables
- [ ] Create user manual for Eva

#### 10.3 Code Quality & Cleanup
- [ ] Run black formatter on all Python files
- [ ] Run ruff linter and fix issues
- [ ] Remove debug print statements
- [ ] Clean up commented-out code
- [ ] Organize imports consistently
- [ ] Add type hints where missing
- [ ] Review and improve error messages

#### 10.4 Repository Organization
- [ ] Clean up project root (move development files to docs/)
- [ ] Organize documentation in docs/ folder
- [ ] Add .editorconfig for consistent formatting
- [ ] Update .gitignore for any missed patterns
- [ ] Archive or delete unnecessary files
- [ ] Tag first release (v0.1.0)

#### 10.5 GitHub Features
- [ ] Set up branch protection rules (require PR reviews)
- [ ] Configure dependabot for security updates
- [ ] Add status badges to README (build status, coverage, etc.)
- [ ] Set up GitHub Pages for documentation (optional)
- [ ] Create GitHub Project board for issue tracking
- [ ] Set up code owners file (.github/CODEOWNERS)

#### 10.6 Final Testing & Validation
- [ ] End-to-end system test
- [ ] Performance benchmarking
- [ ] Security audit checklist
- [ ] Cross-platform testing (if applicable)
- [ ] User acceptance testing
- [ ] Create release notes

**Deliverable**: Polished, documented, GitHub-ready repository

---

## Optional Future Enhancements

### Voice Integration (Post-MVP)
- Add Whisper STT endpoint
- Add Coqui TTS endpoint
- Client-side audio recording
- Streaming audio playback

### Desktop Awareness (V2)
- Screenshot analysis
- Activity monitoring
- Contextual awareness

### Multi-Platform Access (V2)
- Discord bot integration
- Matrix/Signal bots
- Platform adapters

### Advanced Character Features (V2+)
- Goal/skill/desire system
- Held thoughts mechanism
- Adaptive learning (LoRA fine-tuning)
- Full personality evolution

---

## Development Workflow

### Working on a Phase

1. **Create feature branch**: `git checkout -b phase-N-description`
2. **Implement tasks**: Let Claude Code handle detailed implementation
3. **Test locally**: Run tests, manually verify functionality
4. **Review code**: Understand what was implemented and why
5. **Commit and push**: `git commit -am "Phase N: description" && git push`
6. **Create PR** (optional): Review before merging to main
7. **Merge and deploy**: Merge to main, test end-to-end

### Testing Strategy

- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test full user flows
- **Manual testing**: Use the app as a user would

### When Things Break

1. Check logs: `docker-compose logs` and `server/app.log`
2. Run tests: `pytest -v`
3. Isolate the problem: Which phase/component?
4. Fix or rollback: Fix forward or revert commit
5. Add test: Prevent regression

---

## Success Criteria for MVP

### Functional Requirements
- ✅ User can have natural conversations with Eva via text
- ✅ Eva remembers past conversations (two-track memory)
- ✅ Eva generates journal entries in user's style
- ✅ Eva has persistent mood that affects responses
- ✅ System works on multiple platforms (iOS, Android, Desktop)

### Technical Requirements
- ✅ All data stored locally (self-hosted)
- ✅ Responses are generated from local LLM (no external APIs)
- ✅ System handles errors gracefully
- ✅ Memory retrieval is accurate and relevant
- ✅ Performance is acceptable (< 2s response start time)

### Character Quality
- ✅ Responses feel character-appropriate (not tool-like)
- ✅ Character demonstrates memory in natural ways
- ✅ Journal entries sound like user's own writing
- ✅ Character shows consistency across conversations

---

## Notes for Claude Code

When implementing each phase:

1. **Read relevant docs first**: Check design-document.md for context
2. **Follow character-first philosophy**: All user-facing text should come from Eva as a character
3. **Maintain two-track architecture**: Never pollute conversation with context
4. **Write tests**: Include tests with each implementation
5. **Document decisions**: Add comments explaining non-obvious choices
6. **Ask if uncertain**: Use AskUserQuestion if approach is unclear

Remember: The goal is a working system that demonstrates the character companion concept. Perfection can come later - focus on functional first, then optimize.
