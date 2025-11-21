"""
Database Initialization Script

Checks if database is initialized and optionally creates all tables.
Designed to be called from init-database.ps1 startup script.

Exit codes:
    0 - Success (database initialized or already exists)
    1 - Error (connection failed or table creation failed)
    2 - Not initialized (only when --check-only flag used)
"""

import asyncio
import sys
from pathlib import Path

# Add server directory to path so we can import app modules
server_dir = Path(__file__).parent.parent / "server"
sys.path.insert(0, str(server_dir))

from sqlalchemy import text
from app.database import engine, Base

# Import all models so they're registered with Base
from app.models.user import User
from app.models.character import CharacterState
from app.models.conversation import Conversation, ConversationTurn
from app.models.memory import Memory


async def check_database():
    """Check if database is initialized by looking for users table."""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")
            )
            exists = result.scalar()
            return exists
    except Exception as e:
        print(f'ERROR: Database connection failed: {e}', file=sys.stderr)
        sys.exit(1)


async def init_database():
    """Create all database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print('[OK] Database tables created successfully')
        return True
    except Exception as e:
        print(f'ERROR: Failed to create tables: {e}', file=sys.stderr)
        return False


async def main():
    check_only = '--check-only' in sys.argv

    # Check if database is initialized
    is_initialized = await check_database()

    if check_only:
        if is_initialized:
            print('[OK] Database already initialized')
            sys.exit(0)
        else:
            print('Database not initialized')
            sys.exit(2)  # Special code: not initialized
    else:
        # Initialize database
        if is_initialized:
            print('[OK] Database already initialized (skipping)')
            sys.exit(0)
        else:
            print('Initializing database...')
            success = await init_database()
            sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
