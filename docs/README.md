\# Character Companion - Development Guide



\## Project Overview

AI character companion with personality, memory, and journaling capabilities.

Text-first design, voice optional. Self-hosted, privacy-focused.



\## Development Status

**Updated**: 2025-11-21
**Current Phase**: Phase 5 - WebSocket Conversation Endpoint
**Approach**: Claude Code handles implementation, developer reviews and guides

See `../IMPLEMENTATION_PLAN.md` for detailed phase breakdown and tasks.

**Phase 4 Decision**: Changed from WebSocket to Terminal Interface to validate memory system in production-like environment before adding network complexity. WebSocket moved to Phase 5.

**Completed Phases**:
- ✅ Phase 0: Foundation & Infrastructure (2025-11-06)
- ✅ Phase 1: Basic LLM Integration (2025-11-07)
- ✅ Phase 2: Database Schema & Models (2025-11-08)
- ✅ Phase 3: Two-Track Memory System (2025-11-08)
- ✅ Phase 4: Terminal Interface (2025-11-21)
  - **Bonus**: OpenAI API integration (testing until new GPU)
  - **Bonus**: Eva tsundere character personality
  - **Bonus**: Advanced debug system (memory/prompt/llm modes)

**Next**: WebSocket Conversation Endpoint for real-time communication



\## Tech Stack

\- Backend: Python 3.10+, FastAPI, transformers

\- Databases: PostgreSQL, Redis, ChromaDB

\- Frontend: Flutter 3.0+

\- LLM: Phi-3 (microsoft/Phi-3-mini-4k-instruct) via HuggingFace transformers



\## Key Architectural Decisions

1\. Two-track memory: Clean conversation + hidden context

2\. Character-first language (not tool language)

3\. Text-first, voice as optional layer

4\. Native installation (no Docker in prod)



\## How It Works: Two-Track Memory System

The defining innovation of this system is the **two-track architecture** that enables perfect memory without cluttering conversations.

\### The Problem with Traditional RAG

Traditional retrieval-augmented generation systems inject context directly into the conversation history:

```
User: I'm working on an AI project.
Assistant: Tell me about it!
Context: User is working on an AI project ← DUPLICATE!
User: It uses two-track memory.
Context: Project uses two-track memory ← DUPLICATE!
```

**Result**: Wasted tokens, bloated context, less room for actual conversation.

\### Our Solution: Two Separate Tracks

**Track 1 (Conversation)**: Clean, natural dialogue stored in PostgreSQL
```
User: Hi Eva! I'm working on a new AI project.
Assistant: That sounds exciting! What kind of AI project?
User: A character companion that journals.
Assistant: Interesting! *jots down notes*
```

**Track 2 (Context)**: Semantic memories injected ONCE at the top
```
Remember these facts about the user:
- Working on AI character companion project
- Project uses two-track memory system
- Interested in journaling and AI
```

\### Message Flow

```
1. USER SENDS MESSAGE
   ↓
2. STORE IN TRACK 1 (PostgreSQL)
   - Save as clean ConversationTurn
   - Update Redis session state
   ↓
3. BUILD LLM CONTEXT
   ├─ Track 1: Get last 10 conversation turns
   └─ Track 2: Semantic search in ChromaDB
      - Embed user's message → vector
      - Find 5 most relevant memories
      - Inject ONCE at top of context
   ↓
4. LLM GENERATES RESPONSE
   - Phi-3 sees: Context + Clean Conversation
   - Generates character-appropriate response
   ↓
5. PROCESS RESPONSE
   - Store in Track 1 (PostgreSQL)
   - Extract important info → Create new memories
   - Embed and store in ChromaDB (Track 2)
   - Cache recent context in Redis
   ↓
6. SEND TO USER
```

\### Component Roles

| Component | Purpose | When Data Flows In |
|-----------|---------|-------------------|
| **PostgreSQL** | Structured data storage | Every message |
| - ConversationTurn | Track 1: Clean dialogue history | User/Assistant messages |
| - Memory | Track 2: Links to ChromaDB embeddings | Important info detected |
| - User, CharacterState | Persistent user data | User creation, state changes |
| **ChromaDB** | Semantic vector search | When creating memories |
| - Embeddings (384-dim) | Find relevant context by meaning | New memories only |
| - Per-user collections | Isolate memories by user | On memory creation |
| **Redis** | Fast temporary storage | Every interaction |
| - Session state | Track active conversations | Every message |
| - Cache | Avoid repeated DB queries | Every 5 minutes |
| - Active conversation | Know which conv is current | Session start/end |

\### Why This Works

**Efficiency**: Context mentioned once → more room for conversation

**Intelligence**: Semantic search finds relevant memories by meaning, not keywords

**Natural**: Conversation stays clean and readable

**Scalable**: Old memories don't bloat the context window

\### Example: Semantic Search in Action

User asks: **"What project am I working on?"**

ChromaDB searches by semantic similarity (not keywords):
```
Query embedding: [0.23, -0.14, 0.87, ...]
                        ↓
        Finds most similar memories:

1. "User working on AI project - character companion"
   Distance: 1.05 ← Best match!

2. "Project uses two-track memory system"
   Distance: 1.37

3. "User interested in journaling AI"
   Distance: 1.55
```

These get injected as Track 2 context. The LLM now "remembers" the project without it being mentioned in the conversation!



\## Quick Start for Development

```bash
# 1. Start databases
cd docker && docker-compose up -d

# 2. Set up Python environment
cd server
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 5. Run tests
pytest
```



\## Project Documentation

\- `design-document.md` - Full vision, philosophy, and features

\- `technical-architecture.html` - Detailed implementation reference

\- `../IMPLEMENTATION_PLAN.md` - **Phase-by-phase implementation tasks**

\- `../CLAUDE.md` - Guidance for Claude Code sessions

