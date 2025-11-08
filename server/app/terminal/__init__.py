"""
Terminal Interface Module

Interactive terminal interface for conversations with Eva.
Single-user design (qStivi/Stephan).

Usage:
    python -m app.terminal.main
    python -m app.terminal.main --debug

Features:
- Interactive CLI with prompt_toolkit
- Streaming responses with rich
- Command system: /help, /stats, /memories, /mood, /history, /new, /clear, /exit
- Full two-track memory integration
- Conversation persistence across sessions
"""

__all__ = [
    "main",
    "chat_loop",
    "commands",
    "display",
    "session",
]
