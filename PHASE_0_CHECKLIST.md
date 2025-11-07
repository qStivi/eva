# Phase 0: Foundation & Infrastructure - Detailed Checklist

**Goal**: Set up project structure, databases, and basic configuration
**Estimated Time**: 4-6 hours
**Actual Time**: ~40 minutes
**Status**: ✅ Complete (2025-11-06)

*Note: This checklist was used during implementation. For current progress, see IMPLEMENTATION_PLAN.md*

---

## Task 0.1: Project Structure Setup ✅

### 0.1.1 Create .gitignore
**File**: `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
venv/
env/
ENV/

# Environment
.env
.env.local

# Databases
*.db
*.sqlite
*.sqlite3

# LLM Models (too large for git)
*.gguf
*.bin
*.safetensors
models/
checkpoints/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log
logs/
app.log

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Flutter
client/build/
client/.flutter-plugins
client/.flutter-plugins-dependencies
client/.dart_tool/
client/.packages
client/pubspec.lock
client/ios/Pods/
client/ios/.symlinks/
client/android/.gradle/
client/android/local.properties

# Docker volumes (keep compose file)
postgres_data/
redis_data/
chroma_data/
```

**Verify**: File created with no syntax errors

---

### 0.1.2 Initialize Git Repository
**Commands**:
```bash
cd /c/Users/steph/Projects/eva
git init
git config user.name "qStivi"
git config user.email "stephanglaue@outlook.com"
```

**Verify**:
```bash
git status  # Should show "On branch main" or "master"
```

---

### 0.1.3 Initial Commit
**Commands**:
```bash
git add .
git commit -m "Initial commit: Project structure and documentation

- Add project documentation (design-document.md, CLAUDE.md)
- Add implementation plan (IMPLEMENTATION_PLAN.md)
- Add folder structure (docs/, server/, client/, docker/)
- Add .gitignore for Python, Flutter, databases, models"
```

**Verify**:
```bash
git log --oneline  # Should show commit
```

---

### 0.1.4 Create GitHub Repository (Optional)
**Manual Steps**:
1. Go to https://github.com/qStivi
2. Create new repository "eva" (or "character-companion")
3. Set to private (contains personal info)
4. Do NOT initialize with README (we have files already)

**Commands**:
```bash
git remote add origin https://github.com/qStivi/eva.git
git branch -M main
git push -u origin main
```

**Verify**:
```bash
git remote -v  # Should show origin
```

---

## Task 0.2: Server Foundation ✅

### 0.2.1 Create Server Package Structure
**Commands**:
```bash
cd server
touch app/__init__.py
```

**File**: `server/app/__init__.py`
```python
"""
Eva - Character Companion Server
A self-hosted AI character with memory, personality, and journaling.
"""

__version__ = "0.1.0"
```

**Verify**: File exists and is valid Python

---

### 0.2.2 Create Configuration Module
**File**: `server/app/config.py`

```python
"""
Configuration management using pydantic-settings.
Loads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "Eva Character Companion"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8080, validation_alias="PORT")

    # Database URLs
    database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/character_companion",
        validation_alias="DATABASE_URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias="REDIS_URL"
    )
    chroma_host: str = Field(default="localhost", validation_alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, validation_alias="CHROMA_PORT")

    # LLM Configuration
    model_path: Optional[str] = Field(default=None, validation_alias="MODEL_PATH")
    model_context_size: int = Field(default=4096, validation_alias="MODEL_CONTEXT_SIZE")
    model_threads: int = Field(default=8, validation_alias="MODEL_THREADS")
    model_temperature: float = Field(default=0.7, validation_alias="MODEL_TEMPERATURE")

    # Character Configuration
    character_name: str = Field(default="Eva", validation_alias="CHARACTER_NAME")
    default_mood: str = Field(default="neutral", validation_alias="DEFAULT_MOOD")

    # Feature Flags
    voice_enabled: bool = Field(default=False, validation_alias="VOICE_ENABLED")
    journal_enabled: bool = Field(default=True, validation_alias="JOURNAL_ENABLED")

    # Optional Voice
    whisper_model: str = Field(default="base", validation_alias="WHISPER_MODEL")
    tts_enabled: bool = Field(default=False, validation_alias="TTS_ENABLED")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        validation_alias="SECRET_KEY"
    )

    # Logseq Integration
    logseq_directory: Optional[str] = Field(
        default=None,
        validation_alias="LOGSEQ_DIRECTORY"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
```

**Verify**: Python syntax is valid, imports work

---

### 0.2.3 Create FastAPI Application
**File**: `server/app/main.py`

```python
"""
FastAPI application entry point.
Initializes the server, middleware, and routes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Character: {settings.character_name}")

    yield

    # Shutdown
    logger.info("Shutting down gracefully...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI character companion with memory, personality, and journaling",
    lifespan=lifespan
)

# Add CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns server status and basic info.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "character": settings.character_name,
        "debug": settings.debug
    }


@app.get("/")
async def root():
    """
    Root endpoint.
    Returns welcome message.
    """
    return {
        "message": f"Welcome to {settings.app_name}",
        "character": settings.character_name,
        "version": settings.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
```

**Verify**: Python syntax valid, imports resolve (after installing deps)

---

## Task 0.3: Environment Configuration ✅

### 0.3.1 Create .env.example
**File**: `server/.env.example`

```bash
# Application
DEBUG=true
HOST=0.0.0.0
PORT=8080

# Database URLs
DATABASE_URL=postgresql://user:pass@localhost:5432/character_companion
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000

# LLM Configuration
# MODEL_PATH=/path/to/model.gguf
MODEL_CONTEXT_SIZE=4096
MODEL_THREADS=8
MODEL_TEMPERATURE=0.7

# Character Configuration
CHARACTER_NAME=Eva
DEFAULT_MOOD=neutral

# Feature Flags
VOICE_ENABLED=false
JOURNAL_ENABLED=true

# Optional Voice
WHISPER_MODEL=base
TTS_ENABLED=false

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=dev-secret-key-change-in-production

# Logseq Integration (optional)
# LOGSEQ_DIRECTORY=/path/to/logseq/journals
```

**Verify**: File created

---

### 0.3.2 Create .env from Example
**Command**:
```bash
cp .env.example .env
```

**Note**: Edit `.env` later when you have actual model path and Logseq directory

**Verify**:
```bash
cat .env  # Should match .env.example
```

---

## Task 0.4: Database Setup ✅

### 0.4.1 Fix docker-compose.yml
**File**: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: eva_postgres
    environment:
      POSTGRES_DB: character_companion
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d character_companion"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: eva_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    container_name: eva_chromadb
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  chroma_data:
```

**Verify**: YAML syntax is valid

---

### 0.4.2 Start Databases
**Commands**:
```bash
cd docker
docker-compose up -d
```

**Verify**:
```bash
docker-compose ps  # All services should be "Up (healthy)"

# Test PostgreSQL
psql -h localhost -U user -d character_companion -c "SELECT 1;"
# Should return: 1

# Test Redis
redis-cli ping
# Should return: PONG

# Test ChromaDB
curl http://localhost:8000/api/v1/heartbeat
# Should return: {"nanosecond heartbeat": ...}
```

---

### 0.4.3 Create Database Initialization Script (Optional)
**File**: `docker/init.sql` (for future use)

```sql
-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Will add table creation in Phase 2
```

---

## Task 0.5: Python Virtual Environment ✅

### 0.5.1 Create Virtual Environment
**Commands**:
```bash
cd /c/Users/steph/Projects/eva/server
python -m venv venv
```

**Verify**:
```bash
ls venv/Scripts/  # Should see activate, python.exe, etc.
```

---

### 0.5.2 Activate Environment (Git Bash)
**Command**:
```bash
source venv/Scripts/activate
```

**Verify**:
```bash
which python  # Should point to venv/Scripts/python
```

---

### 0.5.3 Update requirements.txt
**File**: `server/requirements.txt`

```txt
# Web Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
alembic>=1.12.0
redis>=5.0.0

# Vector Database
chromadb>=0.4.0

# LLM
llama-cpp-python>=0.2.0

# Data Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Utilities
python-dotenv>=1.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0
black>=23.0.0
ruff>=0.1.0
```

**Verify**: File has proper syntax

---

### 0.5.4 Install Dependencies
**Command**:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Note**: llama-cpp-python may take a while to compile. If you have CUDA, you can install with GPU support:
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

**Verify**:
```bash
pip list | grep fastapi  # Should show version
python -c "import fastapi; print(fastapi.__version__)"
```

---

### 0.5.5 Start FastAPI Server
**Command**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Verify**:
```bash
# In another terminal
curl http://localhost:8080/health
# Should return: {"status": "healthy", ...}

# Check interactive docs
# Open browser: http://localhost:8080/docs
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Starting Eva Character Companion v0.1.0
INFO:     Application startup complete.
```

---

## Task 0.6: Testing Framework ✅

### 0.6.1 Create pytest Configuration
**File**: `server/pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]
ignore = []
```

**Verify**: TOML syntax is valid

---

### 0.6.2 Create pytest Fixtures
**File**: `server/tests/conftest.py`

```python
"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def test_settings():
    """Override settings for testing."""
    settings.debug = True
    settings.database_url = "sqlite:///:memory:"
    return settings


@pytest.fixture(scope="function")
def client():
    """
    Create a test client for FastAPI.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def sample_conversation():
    """Sample conversation data for testing."""
    return {
        "user_id": 1,
        "turns": [
            {"role": "user", "content": "Hello Eva!"},
            {"role": "assistant", "content": "Hey! How are you doing?"},
            {"role": "user", "content": "I'm good, thanks!"},
        ]
    }
```

**Verify**: Python syntax valid

---

### 0.6.3 Create First Test
**File**: `server/tests/test_health.py`

```python
"""
Test health check endpoint.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "character" in data


def test_root_endpoint(client: TestClient):
    """Test the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "character" in data
    assert data["character"] == "Eva"


def test_docs_available(client: TestClient):
    """Test that API docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
```

**Verify**: Python syntax valid

---

### 0.6.4 Run Tests
**Command**:
```bash
pytest
```

**Expected Output**:
```
========================= test session starts =========================
collected 3 items

tests/test_health.py::test_health_check PASSED                  [ 33%]
tests/test_health.py::test_root_endpoint PASSED                 [ 66%]
tests/test_health.py::test_docs_available PASSED                [100%]

========================= 3 passed in 0.50s ==========================
```

**Verify**: All tests pass

---

### 0.6.5 Run with Coverage
**Command**:
```bash
pytest --cov=app --cov-report=html
```

**Verify**:
```bash
# Check coverage report
open htmlcov/index.html  # Or just open in browser
```

---

## Final Phase 0 Verification Checklist ✅

### All Systems Running
```bash
# 1. Databases healthy
docker-compose ps  # All "Up (healthy)"

# 2. FastAPI server running
curl http://localhost:8080/health  # Returns healthy status

# 3. Tests passing
pytest  # All tests pass

# 4. Git repository initialized
git log --oneline  # Shows commits
git remote -v  # Shows origin (if pushed)
```

---

### Git Commit for Phase 0
**Commands**:
```bash
git add .
git commit -m "Phase 0 complete: Foundation & Infrastructure

- Set up project structure with .gitignore
- Initialize FastAPI server with health endpoint
- Configure databases (PostgreSQL, Redis, ChromaDB)
- Create Python virtual environment with dependencies
- Set up testing framework with pytest
- Add configuration management with pydantic-settings
- All tests passing

Deliverable: Running FastAPI server with databases operational"

git push
```

---

## Phase 0 Complete! 🎉

**Deliverables Achieved**:
- ✅ Running FastAPI server with health endpoint
- ✅ All databases operational (PostgreSQL, Redis, ChromaDB)
- ✅ Tests passing
- ✅ Git repository initialized and pushed
- ✅ Development environment fully set up

**Ready for Phase 1**: Basic LLM Integration

**Next Steps**: See `IMPLEMENTATION_PLAN.md` Phase 1 for LLM integration tasks.

---

## Troubleshooting

### Docker services won't start
```bash
# Check if ports are already in use
netstat -an | grep 5432  # PostgreSQL
netstat -an | grep 6379  # Redis
netstat -an | grep 8000  # ChromaDB

# Stop services and remove containers
docker-compose down -v

# Restart
docker-compose up -d
```

### llama-cpp-python install fails
```bash
# Install without GPU support first
pip install llama-cpp-python --no-cache-dir

# Or install pre-built wheels
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

### Tests fail with import errors
```bash
# Make sure venv is activated
source venv/Scripts/activate

# Reinstall in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### FastAPI won't start
```bash
# Check if port 8080 is in use
netstat -an | grep 8080

# Try different port
uvicorn app.main:app --reload --port 8081

# Check logs
tail -f app.log
```
