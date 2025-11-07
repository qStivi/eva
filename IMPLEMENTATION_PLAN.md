# Eva - Implementation Plan

**Created**: 2025-11-06
**Approach**: Claude Code handles implementation, developer guides and reviews
**Goal**: Build working MVP of character companion with memory and journaling

---

## Overview

This plan breaks the project into 6 phases, each with a testable deliverable. Phases build on each other, so testing between phases is critical.

**Timeline Estimate**: 8-12 weeks for full MVP
**Current Phase**: Phase 0 (Foundation)

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

## Phase 1: Basic LLM Integration (Week 2)

**Goal**: Get LLM responding to basic prompts via API endpoint

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
- [ ] Implement model loader with lazy initialization
- [ ] Add model configuration (context size, threads, temperature)
- [ ] Download a small test model (e.g., Llama-3-8B quantized GGUF)
- [ ] Test model loading and inference in isolation
- [ ] Add error handling for missing/invalid models

#### 1.3 Character Prompt System
- [ ] Design Eva's base system prompt (character-first language)
- [ ] Create prompt template with context injection points
- [ ] Implement prompt formatting function
- [ ] Add conversation history formatting
- [ ] Test prompts generate character-appropriate responses

#### 1.4 Simple Generation Endpoint
- [ ] Create `server/app/routes/generate.py`
- [ ] Implement `POST /api/generate` endpoint (simple completion)
- [ ] Accept: prompt text, optional parameters
- [ ] Return: generated text, metadata (tokens, time)
- [ ] Add request/response models with Pydantic
- [ ] Test endpoint with curl/Postman

#### 1.5 Testing
- [ ] Create `server/tests/test_llm_loader.py`
- [ ] Create `server/tests/test_generation.py`
- [ ] Mock LLM for fast testing
- [ ] Test character prompt formatting
- [ ] Test error cases (invalid model, OOM, etc.)

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

## Phase 2: Database Schema & Models (Week 3)

**Goal**: Set up database schemas and ORM models for conversations and memory

### Tasks

#### 2.1 SQLAlchemy Setup
- [ ] Create `server/app/db/__init__.py`
- [ ] Create `server/app/db/base.py` (Base model, engine, session)
- [ ] Create database connection manager
- [ ] Add async session support (SQLAlchemy 2.0 async)
- [ ] Implement session dependency for FastAPI routes

#### 2.2 Database Models
- [ ] Create `server/app/db/models.py`:
  - `User` - User accounts (for multi-user support later)
  - `Conversation` - Conversation sessions
  - `ConversationTurn` - Individual messages
  - `Memory` - Stored memories with metadata
  - `JournalEntry` - Generated journal entries
  - `CharacterState` - Character mood, preferences, etc.

#### 2.3 PostgreSQL Schema Migration
- [ ] Set up Alembic for migrations
- [ ] Create initial migration script
- [ ] Run migration: `alembic upgrade head`
- [ ] Add indexes for common queries
- [ ] Add foreign key constraints

#### 2.4 Redis Session Manager
- [ ] Create `server/app/db/redis_client.py`
- [ ] Implement session storage (conversation state)
- [ ] Add TTL for temporary data
- [ ] Create session CRUD operations
- [ ] Test session persistence and retrieval

#### 2.5 ChromaDB Setup
- [ ] Create `server/app/db/chroma_client.py`
- [ ] Initialize collection for memories
- [ ] Configure embedding function
- [ ] Implement basic add/query operations
- [ ] Test vector search functionality

#### 2.6 Testing
- [ ] Create `server/tests/test_models.py`
- [ ] Create `server/tests/test_database.py`
- [ ] Test CRUD operations for each model
- [ ] Test relationships between models
- [ ] Use test database (pytest fixtures)

**Deliverable**: Complete database layer with models, migrations, and tested CRUD operations

**Testing Checkpoint**:
```python
# In Python shell or test
from app.db.base import SessionLocal
from app.db.models import Conversation, ConversationTurn

session = SessionLocal()
conv = Conversation(user_id=1)
session.add(conv)
session.commit()

turn = ConversationTurn(
    conversation_id=conv.id,
    role="user",
    content="Test message"
)
session.add(turn)
session.commit()
# Should save without errors
```

---

## Phase 3: Memory System - Two-Track Architecture (Week 4)

**Goal**: Implement the core two-track memory system (conversation + context)

### Tasks

#### 3.1 Memory Module Structure
- [ ] Create `server/app/memory/__init__.py`
- [ ] Create `server/app/memory/conversation_track.py` (Track 1)
- [ ] Create `server/app/memory/context_track.py` (Track 2)
- [ ] Create `server/app/memory/retrieval.py` (RAG implementation)

#### 3.2 Track 1: Conversation History
- [ ] Implement conversation history manager
- [ ] Store clean user/assistant messages
- [ ] Format history for LLM context window
- [ ] Implement sliding window (keep recent N turns)
- [ ] Add conversation summarization for old messages
- [ ] Save to PostgreSQL after each turn

#### 3.3 Track 2: Context Injection
- [ ] Implement context manager
- [ ] Store metadata separately from conversation
- [ ] Design context injection format for LLM
- [ ] Support multiple context types:
  - Retrieved memories
  - User preferences
  - Current mood/state
  - Temporal context (time, date)
  - External triggers (webhooks)

#### 3.4 RAG Implementation with ChromaDB
- [ ] Implement embedding generation (use llama.cpp or sentence-transformers)
- [ ] Create memory ingestion pipeline:
  - Take conversation turn
  - Extract meaningful segments
  - Generate embeddings
  - Store in ChromaDB with metadata
- [ ] Implement semantic search:
  - Query based on current message
  - Retrieve top K relevant memories
  - Filter by recency, relevance, importance
- [ ] Add memory importance scoring

#### 3.5 Memory Integration with LLM
- [ ] Update prompt system to include both tracks
- [ ] Format: System prompt + Context + Conversation history
- [ ] Ensure context doesn't pollute conversation
- [ ] Test with multi-turn conversations
- [ ] Verify memory retrieval improves responses

#### 3.6 Testing
- [ ] Create `server/tests/test_memory.py`
- [ ] Test conversation history management
- [ ] Test context injection formatting
- [ ] Test RAG retrieval accuracy
- [ ] Test memory persistence across sessions

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

## Phase 4: WebSocket Conversation Endpoint (Week 5)

**Goal**: Real-time conversation via WebSocket with streaming responses

### Tasks

#### 4.1 WebSocket Infrastructure
- [ ] Create `server/app/routes/conversation.py`
- [ ] Implement `WS /ws/conversation` endpoint
- [ ] Add WebSocket connection manager
- [ ] Handle connection lifecycle (connect, disconnect, errors)
- [ ] Implement authentication (simple token for now)

#### 4.2 Message Protocol
- [ ] Design WebSocket message format (JSON):
  - Client → Server: `{type: "message", content: "...", metadata: {...}}`
  - Server → Client: `{type: "response", content: "...", done: false}`
  - Server → Client: `{type: "error", message: "..."}`
- [ ] Implement message validation
- [ ] Add message type handlers

#### 4.3 Streaming Response Implementation
- [ ] Integrate LLM streaming with llama-cpp-python
- [ ] Stream tokens via WebSocket as generated
- [ ] Send "done" signal when complete
- [ ] Handle stream interruption/cancellation
- [ ] Add typing indicators

#### 4.4 Conversation Session Management
- [ ] Create or resume conversation session
- [ ] Load conversation history from database
- [ ] Retrieve relevant memories from ChromaDB
- [ ] Update session state in Redis
- [ ] Save each turn to PostgreSQL

#### 4.5 Integration
- [ ] Connect WebSocket handler to memory system
- [ ] Connect to LLM generation with streaming
- [ ] Implement full conversation loop:
  1. Receive user message
  2. Load conversation history (Track 1)
  3. Retrieve relevant memories (Track 2)
  4. Format prompt with both tracks
  5. Generate response with streaming
  6. Save turn to database
  7. Update memory embeddings
- [ ] Add error handling and recovery

#### 4.6 Testing
- [ ] Create `server/tests/test_websocket.py`
- [ ] Test WebSocket connection
- [ ] Test message sending/receiving
- [ ] Test streaming responses
- [ ] Test conversation persistence
- [ ] Test memory retrieval during conversation

**Deliverable**: Full WebSocket conversation endpoint with memory and streaming

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

## Phase 5: Flutter Client - Basic UI (Week 6-7)

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
