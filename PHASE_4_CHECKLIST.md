# Phase 4: Terminal Interface - Detailed Checklist

**Goal**: Interactive terminal interface for single-user conversations with Eva
**Estimated Time**: 5-6 hours
**Status**: Starting (2025-11-08)

---

## Overview

Phase 4 builds a terminal interface to test the memory system in a production-like environment before adding WebSocket complexity.

**Key Benefits**:
- Direct validation of two-track memory system
- Visibility into semantic retrieval with `/memories` command
- Single-user simplicity (hardcoded user: qStivi/Stephan)
- Foundation for all other interfaces
- Easier debugging than WebSocket

---

## Task 4.1: Setup & Dependencies - ~15 min

###4.1.1 Add Dependencies
**File**: `server/requirements.txt`

Add:
```txt
# Terminal Interface
prompt-toolkit>=3.0.52
rich>=14.1.0
```

**Verify**: Dependencies listed in requirements.txt

### 4.1.2 Install Dependencies
```bash
cd server
pip install -r requirements.txt
```

**Verify**:
```bash
python -c "import prompt_toolkit; print(prompt_toolkit.__version__)"
python -c "import rich; print(rich.__version__)"
```

### 4.1.3 Create Module Structure
```bash
mkdir server/app/terminal
touch server/app/terminal/__init__.py
touch server/app/terminal/main.py
touch server/app/terminal/chat_loop.py
touch server/app/terminal/commands.py
touch server/app/terminal/display.py
touch server/app/terminal/session.py
```

**Verify**: All files exist

---

## Task 4.2: Session Management - ~45 min

### 4.2.1 Create session.py
**File**: `server/app/terminal/session.py`

**Functions to implement**:

```python
async def load_or_create_user(session: AsyncSession) -> User:
    """
    Load or create hardcoded user "qStivi" / "Stephan".

    Returns user from database, creates if doesn't exist.
    """

async def load_or_create_conversation(
    session: AsyncSession,
    user: User,
    character_state: CharacterState,
) -> Conversation:
    """
    Load most recent conversation or create new one.

    Returns conversation with all history loaded.
    """

async def load_character_state(session: AsyncSession) -> CharacterState:
    """
    Load default character state.

    Creates default state if doesn't exist.
    """

class SessionContext:
    """
    Holds session state for terminal interface.

    Attributes:
        user: User object
        character_state: CharacterState object
        conversation: Current conversation
        debug_mode: Whether debug mode is enabled
    """
```

**Verify**:
```python
# Test functions load/create correctly
async with get_async_session() as db_session:
    user = await load_or_create_user(db_session)
    assert user.username == "qStivi"
    assert user.display_name == "Stephan"
```

---

## Task 4.3: Display Utilities - ~30 min

### 4.3.1 Create display.py
**File**: `server/app/terminal/display.py`

**Functions to implement**:

```python
def display_welcome() -> None:
    """Show welcome banner with rich.Panel"""

def display_user_message(message: str) -> None:
    """Display user message in cyan"""

def display_assistant_message(message: str) -> None:
    """Display Eva's message in green bold"""

def display_system_message(message: str) -> None:
    """Display system message in yellow dim"""

async def display_streaming_response(
    response_iterator,
    console: Console,
) -> str:
    """
    Display streaming response with rich.Live.
    Returns full response text.
    """

def display_stats_table(metadata: Dict) -> None:
    """Display conversation stats with rich.Table"""

def display_memories(memories: List[Dict]) -> None:
    """Display retrieved memories with formatting"""

def display_thinking() -> Status:
    """Return rich.Status for 'Eva is thinking...'"""
```

**Verify**: Each function displays correctly in terminal

---

## Task 4.4: Basic Chat Loop - ~1 hour

### 4.4.1 Create chat_loop.py
**File**: `server/app/terminal/chat_loop.py`

**Main function**:

```python
async def run_chat_loop(
    debug: bool = False
) -> None:
    """
    Main conversation loop.

    1. Initialize session (user, conversation, character state)
    2. Display welcome
    3. Loop:
       - Prompt for input
       - Detect commands (starts with /)
       - Route to handler
       - Continue until /exit
    4. Graceful shutdown
    """
```

**Flow**:
1. Initialize `PromptSession` from prompt_toolkit
2. Load session context
3. Display welcome banner
4. Main loop with `prompt_async("You: ")`
5. Handle Ctrl+C gracefully
6. Commit database changes on exit

**Verify**: Loop starts, accepts input, detects `/exit`

---

## Task 4.5: Message Handler - ~1 hour

### 4.5.1 Implement Message Handling
**File**: `server/app/terminal/chat_loop.py`

**Function**:

```python
async def handle_message(
    user_input: str,
    session_context: SessionContext,
    db_session: AsyncSession,
) -> None:
    """
    Handle user message and generate response.

    1. Display thinking status
    2. Call generate_with_memory()
    3. Stream response with display_streaming_response()
    4. Handle errors
    """
```

**Integration**:
```python
from app.llm.inference import generate_with_memory
from app.terminal.display import display_thinking, display_streaming_response

# Inside handle_message:
with display_thinking():
    response_iterator = await generate_with_memory(
        session=db_session,
        user_id=str(session_context.user.id),
        conversation_id=str(session_context.conversation.id),
        user_message=user_input,
        character_state_id=str(session_context.character_state.id),
        stream=True,
    )

response = await display_streaming_response(response_iterator, console)
```

**Error Handling**:
- LLM timeout
- Database connection errors
- Empty response

**Verify**: Can send message and receive streaming response

---

## Task 4.6: Command System - ~2 hours

### 4.6.1 Create commands.py
**File**: `server/app/terminal/commands.py`

**Commands to implement**:

#### /help
```python
async def cmd_help() -> None:
    """Show available commands"""
    # Display table of commands with descriptions
```

#### /exit or /quit
```python
async def cmd_exit() -> bool:
    """Exit terminal interface"""
    # Return False to signal exit from main loop
```

#### /stats
```python
async def cmd_stats(
    session: AsyncSession,
    conversation_id: str,
) -> None:
    """Show conversation statistics"""
    # Use conversation_history.get_conversation_metadata()
    # Display with display_stats_table()
```

#### /memories
```python
async def cmd_memories(
    session_context: SessionContext,
) -> None:
    """Show last retrieved memories"""
    # Store last retrieved memories in session_context
    # Display with display_memories()
```

#### /new
```python
async def cmd_new(
    session: AsyncSession,
    session_context: SessionContext,
) -> None:
    """Start new conversation"""
    # Create new conversation
    # Update session_context.conversation
```

#### /clear
```python
async def cmd_clear() -> None:
    """Clear screen"""
    # Use rich.console.clear() or os.system('cls'/'clear')
```

#### /mood
```python
async def cmd_mood(
    session: AsyncSession,
    character_state_id: str,
) -> None:
    """Show character state"""
    # Load and display character state
```

#### /history
```python
async def cmd_history(
    session: AsyncSession,
    conversation_id: str,
    n_turns: int = 10,
) -> None:
    """Show recent conversation history"""
    # Load recent turns
    # Display formatted
```

### 4.6.2 Command Router
```python
async def handle_command(
    command: str,
    session_context: SessionContext,
    db_session: AsyncSession,
) -> bool:
    """
    Route command to handler.

    Returns True to continue loop, False to exit.
    """
```

**Verify**: All commands work correctly

---

## Task 4.7: Main Entry Point - ~15 min

### 4.7.1 Create main.py
**File**: `server/app/terminal/main.py`

```python
"""
Terminal Interface Entry Point

Usage:
    python -m app.terminal.main
    python -m app.terminal.main --debug
"""
import asyncio
import argparse
from app.terminal.chat_loop import run_chat_loop

def main():
    parser = argparse.ArgumentParser(
        description="Eva Terminal Interface"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_chat_loop(debug=args.debug))
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            raise

if __name__ == "__main__":
    main()
```

**Verify**:
```bash
python -m app.terminal.main --help
```

---

## Task 4.8: Testing & Polish - ~1 hour

### 4.8.1 Manual Testing

**Test Multi-Turn Conversation**:
```
You: Hello Eva!
Eva: Hey! How's it going?
You: I love pizza
Eva: Nice! I'll remember that.
You: What do I like to eat?
Eva: I remember you mentioned loving pizza!
```

**Test /memories Command**:
```
You: /memories
╭─ Retrieved Memories ───────────────────╮
│ 1. [Preference, score: 0.89]           │
│    "User likes pizza"                  │
╰────────────────────────────────────────╯
```

**Test /stats Command**:
```
You: /stats
╭─ Conversation Statistics ──────────────╮
│ Total Turns:      6                    │
│ User Turns:       3                    │
│ Assistant Turns:  3                    │
│ Started:          2025-11-08 10:00:00  │
╰────────────────────────────────────────╯
```

**Test Conversation Persistence**:
1. Start conversation
2. Send several messages
3. Exit with `/exit`
4. Restart: `python -m app.terminal.main`
5. Verify conversation history loads

### 4.8.2 Error Handling

**Test empty input**:
```
You:
You:
```

**Test very long message**:
```
You: [paste 1000-word message]
```

**Test database not running**:
```bash
# Stop Docker containers
docker-compose down

# Try to start terminal
python -m app.terminal.main
# Should show friendly error message
```

### 4.8.3 Polish

- [ ] Verify colors display correctly on Windows
- [ ] Test command history (up/down arrows)
- [ ] Test streaming response smoothness
- [ ] Verify graceful Ctrl+C handling
- [ ] Check all error messages are helpful

---

## Task 4.9: Documentation - ~15 min

### 4.9.1 Update TIME_LOG.md
Add Phase 4 entry with:
- Start/end times
- Actual time spent
- Any issues encountered

### 4.9.2 Update IMPLEMENTATION_PLAN.md
Mark Phase 4 complete with:
- Completion checkmark
- Actual vs estimated time
- Results and deliverables

### 4.9.3 Create TERMINAL_USAGE.md (Optional)
**File**: `docs/TERMINAL_USAGE.md`

Quick start guide:
- Installation
- Running the terminal
- Available commands
- Tips and tricks

---

## Final Verification Checklist

```bash
# 1. Terminal starts successfully
python -m app.terminal.main

# 2. Can have conversation
You: Hello!
Eva: [responds]

# 3. Memory system works
You: I like cats
You: What do I like?
Eva: [mentions cats]

# 4. Commands work
You: /help     # Shows commands
You: /stats    # Shows stats
You: /memories # Shows retrieved memories
You: /new      # Starts new conversation
You: /exit     # Exits gracefully

# 5. Persistence works
# Exit and restart
python -m app.terminal.main
# Conversation history should resume

# 6. Error handling works
# [empty input, long input, database down]
```

---

## Git Commit for Phase 4

```bash
git add .
git commit -m "Phase 4 complete: Terminal Interface

- Interactive CLI for conversations with Eva
- Single-user design (qStivi/Stephan)
- Full memory integration with two-track system
- Command system: /help, /stats, /memories, /mood, /history, /new, /clear, /exit
- Streaming response display with rich
- Conversation persistence across sessions
- Debug mode with --debug flag

Files created:
- server/app/terminal/main.py
- server/app/terminal/chat_loop.py
- server/app/terminal/commands.py
- server/app/terminal/display.py
- server/app/terminal/session.py

Files updated:
- server/requirements.txt (prompt-toolkit, rich)

Deliverable: Working terminal interface for testing memory system

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

## Phase 4 Complete! 🎉

**Deliverables Achieved**:
- ✅ Interactive terminal conversation with Eva
- ✅ Full two-track memory integration
- ✅ Command system for debugging and control
- ✅ Streaming responses
- ✅ Conversation persistence
- ✅ Single-user experience (qStivi/Stephan)
- ✅ Production-like testing environment

**Ready for Phase 5**: WebSocket Conversation Endpoint (with proven memory system)
