# Eva - Current Project Status

**Last Updated**: 2025-11-21
**Current Phase**: Phase 6 (Flutter Client)
**Development Approach**: Claude Code handles implementation, developer reviews and guides

---

## Quick Status

✅ **Working**: Terminal interface + WebSocket endpoint with full memory system, streaming, API integration
🔄 **Next**: Flutter cross-platform client
📅 **Timeline**: ~8-12 weeks for full MVP (currently ~50% complete)

---

## Completed Phases

### Phase 0: Foundation & Infrastructure ✅
**Completed**: 2025-11-06 (~40 minutes)
- FastAPI server with health endpoints
- Docker services (PostgreSQL, Redis, ChromaDB)
- Python virtual environment setup
- Testing framework with pytest

### Phase 1: Basic LLM Integration ✅
**Completed**: 2025-11-07 (~2.5 hours)
- Transformers library integration (HuggingFace)
- Model: microsoft/Phi-3-mini-4k-instruct (3.8B params)
- Character prompt system (Eva personality)
- Simple generation endpoint

### Phase 2: Database Schema & Models ✅
**Completed**: 2025-11-08 (~2 hours)
- SQLAlchemy async ORM setup
- PostgreSQL models (User, Conversation, Memory, Journal, CharacterState)
- Redis session manager
- ChromaDB vector storage
- Alembic migrations

### Phase 3: Two-Track Memory System ✅
**Completed**: 2025-11-08 (~2.5 hours)
- Track 1: Clean conversation history
- Track 2: Side context injection (memories, preferences, mood)
- RAG implementation with ChromaDB
- Memory importance scoring
- Semantic search for relevant memories

### Phase 4: Terminal Interface ✅
**Completed**: 2025-11-21 (~5-6 hours total across multiple sessions)

**Initial Implementation** (2025-11-08):
- Interactive CLI with prompt_toolkit + rich
- Command system (/help, /exit, /stats, /memories, /new, /clear, /mood, /history)
- Streaming response display
- Conversation persistence
- Single-user design (qStivi/Stephan)

**Enhancements** (2025-11-21):
- **OpenAI API Integration**: Switchable API mode (USE_API=true/false)
  - Fast testing without 5-minute model loading
  - GPT-4o-mini: ~$1.35/month for 100 conversations/day
  - Higher token limits (1024 vs 256)
- **Eva Character**: Tsundere fox girl personality (sass, deflection, hidden care)
- **Debug System**: Three modes (/debug memory/prompt/llm)
  - Memory: Show retrieval queries, relevance scores
  - Prompt: Display full message structure
  - LLM: Show model info, generation params
- **Performance**: Increased history (100 turns), better context

### Phase 5: WebSocket Conversation Endpoint ✅
**Completed**: 2025-11-21 (~6 hours)

**Implementation**:
- **WebSocket Infrastructure**: `/ws/conversation` endpoint with connection manager
- **Message Protocol**: Pydantic models for validation
  - Client → Server: `{type: "message", content: "..."}`
  - Server → Client: `{type: "response_chunk", content: "...", done: false/true}`
  - Server → Client: `{type: "error", code: "...", message: "..."}`
  - Server → Client: `{type: "system", event: "...", data: {...}}`
- **Authentication**: Token-based using SECRET_KEY from config
- **Session Management**: Redis-backed with 1-hour TTL auto-cleanup
- **Streaming**: Reuses `generate_with_memory` from terminal
- **Error Handling**: Sanitized errors (no stack traces to client)
- **Testing**: Python test client, verified streaming (45 chunks, 7.4s)

**Key Files**:
- `server/app/routes/conversation.py`: WebSocket endpoint
- `server/app/websocket/connection_manager.py`: Connection lifecycle
- `server/app/websocket/message_protocol.py`: Message validation
- `server/app/websocket/session_manager.py`: Redis session state
- `server/test_websocket_client.py`: Test client

---

## Next Phase: Phase 6 - Flutter Client

**Estimated Time**: 8-12 hours
**Goal**: Cross-platform Flutter app with text chat interface

### Key Tasks:
- [ ] Flutter project setup (iOS, Android, Desktop, Web)
- [ ] WebSocket client integration
- [ ] Chat UI with streaming response display
- [ ] State management (Riverpod/Provider)
- [ ] Local storage for offline mode
- [ ] Testing on multiple platforms

**Why This Phase**:
- WebSocket endpoint is ready and working
- Multi-platform deployment (mobile, desktop, web)
- Native-feeling UI with Flutter
- Foundation for voice features (Phase 7+)

---

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **LLM**:
  - Local: Phi-3-mini-4k-instruct (HuggingFace transformers)
  - API: GPT-4o-mini (testing mode until new GPU)
- **Databases**:
  - PostgreSQL (structured data)
  - Redis (sessions, caching)
  - ChromaDB (vector embeddings)

### Frontend (Planned - Phase 6)
- **Framework**: Flutter 3.0+
- **Platforms**: iOS, Android, Desktop, Web
- **Features**: Text chat, voice recording (optional), journal viewer

### Deployment (Future)
- **Platform**: Proxmox Container (native, no Docker in production)
- **Services**: Systemd units
- **Proxy**: Nginx with SSL/TLS

---

## Key Features Implemented

### Two-Track Memory Architecture
**The defining innovation of this project**

**Problem with traditional RAG**: Context duplication wastes tokens
```
User: I'm working on an AI project.
Context: User is working on an AI project ← DUPLICATE!
```

**Our Solution**: Separate tracks
- **Track 1** (Conversation): Clean dialogue only
- **Track 2** (Context): Memories injected separately at top

Result: 40-60% token savings, cleaner conversations

### Character-First Design
All interactions from Eva's perspective as a character, not a tool:
- ✅ "That's interesting! *jots down notes*"
- ❌ "I've saved that to your journal"

### Privacy & Self-Hosting
- All data stored locally
- Local LLM processing (or user-controlled API)
- No external dependencies
- Complete data ownership

---

## Project Structure

```
eva/
├── docs/                       # Documentation (you are here!)
│   ├── CURRENT_STATUS.md       # This file - project status
│   ├── IMPLEMENTATION_PLAN.md  # Detailed phase breakdown
│   ├── TIME_LOG.md             # Actual development time tracking
│   ├── README.md               # Project overview
│   ├── design-document.md      # Long-term vision & philosophy
│   ├── SKILL_FILE_SYSTEM.md    # Modular prompt architecture
│   ├── STARTUP.md              # Startup script documentation
│   └── research/               # Research files
│       ├── anthropicPricing.txt
│       ├── openaiPrices.txt
│       └── base Character Idea.txt
├── archive/                    # Completed phase checklists
│   ├── PHASE_0_CHECKLIST.md
│   ├── PHASE_3_CHECKLIST.md
│   └── PHASE_4_CHECKLIST.md
├── server/                     # Python backend
│   ├── app/                    # Core application
│   │   ├── llm/                # LLM integration
│   │   ├── memory/             # Two-track memory system
│   │   ├── terminal/           # Terminal interface
│   │   ├── models/             # Database models
│   │   └── routes/             # API endpoints (future)
│   ├── tests/                  # Test suite
│   ├── alembic/                # Database migrations
│   └── requirements.txt        # Python dependencies
├── docker/                     # Development databases
│   └── docker-compose.yml      # PostgreSQL, Redis, ChromaDB
├── scripts/                    # Utility scripts
└── CLAUDE.md                   # Instructions for Claude Code
```

---

## Quick Commands

### Start Development Server
```bash
# Option 1: Start databases + terminal interface
.\scripts\start-dev.ps1

# Option 2: Manual start
cd docker && docker-compose up -d
cd ../server && source venv/Scripts/activate
python -m app.terminal.main
```

### Run Tests
```bash
cd server
pytest                    # All tests
pytest -v                 # Verbose
pytest tests/test_memory.py  # Specific test
```

### Database Operations
```bash
# Migrations
cd server
alembic upgrade head      # Apply migrations
alembic revision -m "msg" # Create new migration

# Access databases
psql -h localhost -U user -d character_companion
redis-cli
# ChromaDB: http://localhost:8000
```

### Terminal Interface Commands
```
/help       - Show all commands
/debug      - Toggle debug modes (memory, prompt, llm)
/memories   - Show last retrieved memories
/history    - Show conversation history
/stats      - Show conversation statistics
/mood       - Show character state
/new        - Start new conversation
/restart    - Restart terminal
/exit       - Exit gracefully
```

---

## Development Workflow

### Current Session
1. Pull latest: `git pull`
2. Start services: `.\scripts\start-dev.ps1` (or `docker-compose up -d`)
3. Activate venv: `source server/venv/Scripts/activate`
4. Run terminal: `python -m app.terminal.main`
5. Test changes
6. Commit + push frequently (after each working state)

### For New Features
1. Create feature branch: `git checkout -b feature/websocket-endpoint`
2. Implement (let Claude Code handle details)
3. Test locally
4. Review and understand changes
5. Commit: `git commit -am "Add WebSocket endpoint"`
6. Push: `git push -u origin feature/websocket-endpoint`
7. Merge to main after validation

---

## Configuration

### Environment Variables (.env)

**API Mode (Current - Testing)**:
```bash
USE_API=true
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

**Local Model Mode (Production with GPU)**:
```bash
USE_API=false
MODEL_PATH=microsoft/Phi-3-mini-4k-instruct
MODEL_CONTEXT_SIZE=4096
MODEL_TEMPERATURE=0.7
```

**Databases**:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/character_companion
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

---

## Known Issues & Considerations

### Current Limitations
1. **Single-user only**: Hardcoded user "qStivi"/"Stephan" (multi-user support in Phase 7+)
2. **No GUI yet**: Terminal + WebSocket only (Flutter client in Phase 6)
3. **Local model slow**: GTX 1050 Ti struggles with 3.8B model (using API until GPU upgrade)
4. **No Logseq integration yet**: Planned for Phase 7

### Technical Debt
- None! Clean separation of concerns, well-tested
- Skill file system documented but not yet implemented (Phase 6-7)

---

## Success Metrics (MVP)

### Functional ✅
- [x] Natural conversations with Eva
- [x] Two-track memory system working
- [x] Terminal interface operational
- [x] WebSocket for real-time communication
- [ ] Flutter client (Phase 6)
- [ ] Journal integration (Phase 7)

### Technical ✅
- [x] All data stored locally
- [x] Memory retrieval accurate and relevant
- [x] Performance acceptable (<2s response start)
- [x] Error handling graceful
- [ ] Production deployment ready (Phase 9)

### Character Quality ✅
- [x] Character-appropriate responses (not tool-like)
- [x] Memory demonstrated naturally
- [x] Consistent personality across sessions
- [ ] Mood system affecting responses (Phase 7)

---

## Next Steps (Immediate)

1. **Review and plan Phase 5**: WebSocket endpoint architecture
2. **Test current system thoroughly**: Find any bugs before adding complexity
3. **Document API**: Once WebSocket is ready, document message protocol
4. **Prepare for Flutter**: Design API contract that Flutter client will use

---

## Resources

- **GitHub**: https://github.com/qStivi/eva
- **Documentation**: See `docs/` folder for detailed guides
- **Issue Tracking**: Use GitHub Issues
- **Development Log**: See `docs/TIME_LOG.md` for session history

---

**Remember**: This is a character companion, not a tool. Eva has personality, boundaries, and opinions. The system should always reflect this in every interaction.
