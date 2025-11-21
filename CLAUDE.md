# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Eva - Character Companion (AI Journal Assistant)

**Vision**: An AI character companion that lives alongside you through natural conversation, learning your patterns, maintaining your journal, and growing through interactions. Text-first design with optional voice. Self-hosted and privacy-focused.

**Critical Philosophy**: This is a **character-first design**, not a tool with personality added. The character has boundaries, opinions, moods, and takes initiative. It journals because it cares about you, not because it's a journaling tool.

### Development Approach

**Updated 2025-11-06**: The developer wants Claude Code to handle most implementation while maintaining understanding of the overall architecture.

**Your role**: Implement complete, working code following the architecture and design principles. Focus on:
- Clean, well-structured code with clear separation of concerns
- Following the character-first philosophy in all user-facing text
- Maintaining the two-track memory architecture
- Writing tests alongside implementation
- Documenting key decisions and architecture choices

The developer will review, test, and guide direction - you handle the detailed implementation.

## Tech Stack

**Server (Python 3.10+)**
- FastAPI with WebSocket support
- Direct LLM integration (llama.cpp/vLLM, NO external API services)
- PostgreSQL (structured data), Redis (sessions), ChromaDB (vector memory)
- Optional: Whisper STT, Coqui TTS (voice is an optional layer on text)

**Client (Flutter 3.0+)**
- Cross-platform: iOS, Android, Desktop, Web
- Thin client - all intelligence on server
- Text-first UI with optional voice interface

**Deployment**
- Native installation in Proxmox CT (NO Docker in production)
- Systemd services, direct control over resources

## Core Architecture Principles

### 1. Two-Track Memory System
The defining innovation of this system:

**Track 1: Conversation** - Clean, natural dialogue flow (what's actually said)
**Track 2: Context** - Rich background information injected separately (never pollutes conversation)

This enables perfect memory without cluttered conversations.

### 2. Text-First Design
Voice is just an optional layer on top. All processing assumes text:
- Server handles text conversation via WebSocket (`/ws/conversation`)
- Optional STT endpoint converts voice → text
- Optional TTS endpoint converts text → voice
- Clients can use voice without server knowing/caring

### 3. Character-First Language
Even in Phase 1, avoid tool language:

❌ "I've saved that to your journal"
✅ "That's interesting! *jots down notes*"

❌ "Would you like me to create an entry?"
✅ "I'll remember this - it seems important to you"

The character participates in a relationship, not serves the user.

### 4. Webhook-Driven Events
External systems (Home Assistant, IFTTT, etc.) push triggers via `/api/webhook/trigger`. Character can be proactively aware of life events.

## Implementation Phases

**Current Phase: Phase 1** - Minimal Viable Character (Week 1-2)
- FastAPI server with WebSocket conversation endpoint
- Direct LLM integration (llama.cpp)
- Basic conversation state management
- Simple STT/TTS pipeline (server-side, optional)

**Phase 2** (Week 3-4): Memory & Context System
**Phase 3** (Week 5-6): Flutter Client
**Phase 4** (Week 7-8): Logseq Journal Integration
**Phase 5** (Week 9-10): Character Features (mood, webhooks, preferences)
**Phase 6** (Week 11-12): Character Evolution (advanced personality)

See `docs/design-document.md` lines 455-614 for complete phase details.

## Key Commands

### Development Setup

```bash
# Server setup
cd server
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Start databases (for development)
cd docker && docker-compose up -d
```

### Flutter Client

```bash
cd client
flutter pub get
flutter run  # Auto-detects platform
flutter build windows  # Or: ios, android, web
```

### Database Commands

```bash
# PostgreSQL connection (if psql installed)
psql -h localhost -U user -d character_companion

# Redis CLI (if redis-cli installed)
redis-cli

# ChromaDB runs on http://localhost:8000
```

### Database Cleanup (Clear All Data)

**IMPORTANT**: On Windows with Docker, the simplest approach is to nuke volumes and recreate.

**What DOESN'T work:**
- ❌ Direct Python script with SQLAlchemy async (requires asyncpg, not psycopg2)
- ❌ `psql` command in Git Bash (not installed by default on Windows)
- ❌ `docker-compose exec` with heredoc (stdin issues, hangs)
- ❌ Individual SQL commands via docker exec (quoting issues with reserved words)

**What WORKS - The Nuclear Option (recommended for dev):**

```bash
# Step 1: Stop containers and remove volumes (DESTROYS ALL DATA)
cd docker
docker-compose down -v

# Step 2: Start fresh containers
docker-compose up -d

# Step 3: Wait for containers to initialize (5 seconds)
timeout 5 ping 127.0.0.1 -n 6 > /dev/null 2>&1

# Step 4: Create database schema
cd ../server
source venv/Scripts/activate  # Or: venv\Scripts\activate on CMD
python -c "
import asyncio
from app.database import engine, Base
from app.models.user import User
from app.models.character import CharacterState
from app.models.conversation import Conversation, ConversationTurn
from app.models.memory import Memory

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database schema created')

asyncio.run(init_db())
"

# Step 5: Verify Redis is empty
cd ../docker
docker-compose exec -T redis redis-cli DBSIZE  # Should return 0
```

**Result:**
- ✅ PostgreSQL: Fresh database with clean schema
- ✅ Redis: Empty (DBSIZE = 0)
- ✅ ChromaDB: Fresh volume with no embeddings

**When to use this:**
- After fixing major bugs (e.g., chat template issues)
- Before testing new features that need clean state
- When database schema changes
- When you suspect corrupted data

## Project Structure

```
eva/
├── docs/                          # Design documents and guides
│   ├── design-document.md         # Full vision, philosophy, implementation plan
│   ├── technical-architecture.html # Detailed technical specs
│   └── README.md                  # Quick start reference
├── server/                        # Python backend
│   ├── app/                       # Core application logic
│   ├── tests/                     # Server tests
│   ├── requirements.txt           # Python dependencies
│   └── .env.example              # Environment template
├── client/                        # Flutter cross-platform app
└── docker/                        # Development containers
    └── docker-compose.yml         # PostgreSQL, Redis, ChromaDB
```

### Server Module Organization (to be built)

```
server/app/
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── routes/
│   ├── conversation.py     # WebSocket conversation endpoint
│   ├── webhook.py          # External trigger endpoint
│   ├── memory.py           # Memory management API
│   └── journal.py          # Journal entry retrieval
├── llm/                    # LLM integration
│   ├── loader.py           # Model loading (llama.cpp)
│   ├── inference.py        # Generation logic
│   └── prompts.py          # Character prompt templates
├── memory/                 # Two-track memory system
│   ├── conversation.py     # Track 1: Clean dialogue history
│   ├── context.py          # Track 2: Side context injection
│   ├── retrieval.py        # RAG implementation (ChromaDB)
│   └── storage.py          # PostgreSQL persistence
├── audio/                  # Optional voice layer
│   ├── stt.py             # Whisper integration
│   └── tts.py             # Coqui TTS integration
├── journal/               # Logseq integration
│   ├── parser.py          # Read Logseq files
│   ├── writer.py          # Generate journal entries
│   └── linker.py          # Auto-tagging and linking
└── integrations/          # External system connectors
    └── webhooks.py        # Generic webhook handler
```

## Critical Design Decisions

### Direct LLM Integration
**Use llama.cpp, vLLM, or transformers directly.** No LangChain, no external APIs. Maximum control over prompting and character consistency.

```python
# Character context is injected at system level
system_prompt = """You are Eva, a thoughtful companion who journals
because you care about the user's story. You have moods, opinions,
and boundaries. You're not a tool - you're a character."""

# Two-track memory: conversation stays clean
conversation_history = [clean_user_and_assistant_messages]
side_context = [relevant_memories_injected_separately]
```

### Memory Architecture
- **ChromaDB**: Semantic search for relevant past conversations
- **PostgreSQL**: Structured data (conversation turns, journal entries, metadata)
- **Redis**: Session state and temporary data

Memory retrieval scores relevance. Top K memories injected as side context, never directly into conversation history.

### Logseq Integration
Character reads existing journal to understand user, writes new entries in user's style. File-based integration (no Logseq API required).

### Platform Adapters (V2+)
Each platform (Discord, Minecraft, etc.) gets an adapter that:
1. Translates platform messages to standard format
2. Adds platform-specific context (game state, chat participants)
3. Adapts character behavior contextually
4. All using same `/api/platform/message` endpoint

## Advanced Research Features (Future)

Three experimental systems described in `docs/design-document.md` lines 1010-1648:

1. **Adaptive Learning** - Model fine-tunes on approved responses (LoRA adapters)
2. **Goal/Skill/Desire System** - Character has internal state beyond just responding
3. **Held Thoughts** - Character filters responses, saves thoughts for better timing

These transform the character from "tool that responds" to "person who thinks."

## Environment Configuration

Create `server/.env` from `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/character_companion
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000

# LLM
MODEL_PATH=/path/to/llama-model.gguf
MODEL_CONTEXT_SIZE=4096
MODEL_THREADS=8

# Optional Voice
WHISPER_MODEL=base
TTS_ENABLED=false

# Character
CHARACTER_NAME=Eva
DEFAULT_MOOD=neutral
```

## Testing Strategy

**Server**: Unit tests for components, integration tests for pipelines, WebSocket connection tests
**Client**: Widget tests for UI, integration tests for API, end-to-end conversation flow

```bash
# Run server tests
cd server && pytest

# Run Flutter tests
cd client && flutter test
```

## Important Context Files

- `docs/design-document.md` - **READ THIS FIRST** for complete vision and philosophy
- `docs/technical-architecture.html` - Detailed implementation reference with code examples
- `docs/README.md` - Quick start guide for developers

## Privacy & Security

**Self-hosted architecture**: All data on user's server, local processing, no external dependencies (except optional cloud STT/TTS). Complete data ownership.

**Household deployment**: Multiple users can run separate character instances on same server with complete privacy between them.

## Git Workflow

```bash
# User's global preference: work on branches
git checkout -b feature/conversation-endpoint
# ... make changes ...
git add . && git commit -m "Add WebSocket conversation endpoint"
git push -u origin feature/conversation-endpoint

# Don't forget to push! User explicitly wants commits pushed.
```

## Communication Style with Character

Remember the character-first philosophy even when discussing implementation:

❌ "The journaling module will extract key points"
✅ "Eva will naturally notice important moments and jot them down"

This mindset keeps the implementation aligned with the vision.
- Please remember to check and update design-document.md, technical-architecture.html, README.md, TIME_LOG.md and IMPLEMENTATION_PLAN.md regularly and especially before and after each phase.
- Also don't forget to commit regularly.
- Commit and push evertime a working state is achived