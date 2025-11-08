\# Character Companion - Development Guide



\## Project Overview

AI character companion with personality, memory, and journaling capabilities.

Text-first design, voice optional. Self-hosted, privacy-focused.



\## Development Status

**Updated**: 2025-11-07
**Current Phase**: Phase 2 - Database Schema & Models
**Approach**: Claude Code handles implementation, developer reviews and guides

See `../IMPLEMENTATION_PLAN.md` for detailed phase breakdown and tasks.



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

