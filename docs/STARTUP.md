# Eva - Startup Guide

Quick reference for starting and managing the Eva development environment.

## Quick Start

**PowerShell (Recommended):**
```powershell
.\scripts\start-dev.ps1
```

**Batch (Fallback):**
```cmd
.\scripts\start-dev.bat
```

**Manual (If scripts fail):**
```bash
# 1. Start Docker services
cd docker
docker-compose up -d

# 2. Wait for services (check manually)
docker-compose ps  # All should be "Up (healthy)"

# 3. Start terminal
cd ../server
source venv/Scripts/activate  # Git Bash
# OR: venv\Scripts\activate.bat  # CMD
# OR: venv\Scripts\Activate.ps1  # PowerShell
python -m app.terminal.main
```

---

## What the Startup Script Does

1. ✅ **Checks prerequisites** (Docker, Python, venv)
2. ✅ **Starts Docker services** (PostgreSQL, Redis, ChromaDB)
   - Skips if already running
3. ✅ **Waits for health checks** (up to 60 seconds)
4. ✅ **Initializes database** (asks for confirmation if needed)
5. ✅ **Launches terminal interface**
6. ✅ **Supports /restart** command (auto-relaunches after 5 seconds)
7. ✅ **Asks about Docker cleanup** on exit

---

## Command Line Options

### PowerShell Script Options

```powershell
# Enable debug mode
.\scripts\start-dev.ps1 -Debug

# Skip Docker startup (if already running)
.\scripts\start-dev.ps1 -SkipDocker

# Skip database initialization check
.\scripts\start-dev.ps1 -SkipDbInit

# Combine options
.\scripts\start-dev.ps1 -Debug -SkipDocker
```

### Terminal Interface Options

```bash
# Start with debug output
python -m app.terminal.main --debug
```

---

## Terminal Commands

Once Eva is running, use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/exit` or `/quit` | Exit the interface |
| `/restart` | Restart the interface (auto-relaunches after 5 sec) |
| `/stats` | Show conversation statistics |
| `/memories` | Show last retrieved memories |
| `/new` | Start a new conversation |
| `/clear` | Clear the terminal screen |
| `/mood` | Show Eva's current mood and state |
| `/history [n]` | Show recent conversation (default: 10 turns) |

---

## Troubleshooting

### "Docker daemon not running"

**Solution:**
1. Start Docker Desktop
2. Wait for it to fully start (whale icon in system tray should be steady)
3. Run script again

### "Services failed to become healthy"

**Check service status:**
```bash
cd docker
docker-compose ps
docker-compose logs
```

**Common fixes:**
```bash
# Restart services
docker-compose restart

# Full reset (DESTROYS DATA!)
docker-compose down -v
docker-compose up -d
```

### "Virtual environment not found"

**Solution:**
```bash
cd server
python -m venv venv
pip install -r requirements.txt
```

### "Database connection failed"

**Check PostgreSQL is running:**
```bash
cd docker
docker-compose exec postgres pg_isready -U user -d character_companion
```

**If fails, restart PostgreSQL:**
```bash
docker-compose restart postgres
```

### Services take too long to start

**Normal startup times:**
- PostgreSQL: 5-10 seconds
- Redis: 2-5 seconds
- ChromaDB: 5-15 seconds

**If timeout (60s) is hit:**
1. Check Docker Desktop resource allocation (Settings → Resources)
2. Check for port conflicts: `netstat -ano | findstr "5432 6379 8000"`
3. Restart Docker Desktop

### "/restart doesn't work"

**Requirements:**
- Must use `start-dev.ps1` or `start-dev.bat` (not manual Python launch)
- Exit code 99 must be detected by script

**Manual workaround:**
1. Type `/exit`
2. Run `.\scripts\start-dev.ps1` again

---

## Development Workflows

### Daily Development (Fast Restart)

```powershell
# First time today
.\scripts\start-dev.ps1

# Use /exit when done
# Choose "N" when asked "Stop Docker containers?"

# Next time (instant startup)
.\scripts\start-dev.ps1  # Skips Docker start, instant!
```

### Clean Restart (Reset Everything)

```powershell
# Exit terminal if running
/exit
# Choose "Y" to stop Docker

# Then do full reset
cd docker
docker-compose down -v  # DESTROYS ALL DATA
cd ..
.\scripts\start-dev.ps1  # Fresh start
```

### Testing Memory Changes

```powershell
# Reset database only (keeps Docker running)
cd server
source venv/Scripts/activate
python -c "
import asyncio
from app.database import drop_db, init_db
asyncio.run(drop_db())
asyncio.run(init_db())
"

# Or use /restart in terminal
/restart
```

### Switching Models

```bash
# 1. Stop terminal (/exit)
# 2. Edit server/.env
#    MODEL_PATH=/path/to/new/model.gguf
# 3. Restart
.\scripts\start-dev.ps1
```

---

## Script Internals

### Health Check Logic (`wait-for-services.ps1`)

Polls services every 2 seconds:
- PostgreSQL: `pg_isready -U user -d character_companion`
- Redis: `redis-cli ping` (expects "PONG")
- ChromaDB: `http://localhost:8000/api/v1/heartbeat` (expects HTTP 200)

Timeout: 60 seconds

### Database Init Logic (`init-database.ps1`)

1. Checks if `users` table exists
2. If not: Creates all tables via SQLAlchemy metadata
3. Exit codes:
   - 0: Already initialized
   - 2: Not initialized (triggers prompt)
   - 1: Error

### Restart Loop Logic

```powershell
# start-dev.ps1 restart loop
while ($RestartLoop) {
    python -m app.terminal.main
    if ($ExitCode -eq 99) {
        # /restart was used
        Start-Sleep -Seconds 5
        continue
    } else {
        # Normal exit
        break
    }
}
```

---

## Environment Variables

See `server/.env.example` for full list. Key variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/character_companion
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000

# LLM
MODEL_PATH=/path/to/model.gguf
MODEL_CONTEXT_SIZE=4096
MODEL_THREADS=8

# Character
CHARACTER_NAME=Eva
DEFAULT_MOOD=curious

# Debug
DEBUG=false  # Set to "true" for detailed logging
```

---

## Advanced: Manual Service Management

### Start services individually

```bash
cd docker

# Start only PostgreSQL
docker-compose up -d postgres

# Start only Redis
docker-compose up -d redis

# Start only ChromaDB
docker-compose up -d chromadb
```

### Check service health

```bash
# PostgreSQL
docker-compose exec postgres pg_isready -U user -d character_companion

# Redis
docker-compose exec redis redis-cli ping

# ChromaDB
curl http://localhost:8000/api/v1/heartbeat
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f chromadb

# Last 50 lines
docker-compose logs --tail=50 postgres
```

---

## Next Steps

- Read [Design Document](design-document.md) for project vision
- Check [Implementation Plan](../IMPLEMENTATION_PLAN.md) for development status
- Review [Technical Architecture](technical-architecture.html) for system details

---

**Questions?** Check the main [README](README.md) or file an issue.
