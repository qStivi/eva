"""
Memory System - Two-Track Architecture

This module implements Eva's core memory system with two distinct tracks:

Track 1 (Conversation): Clean dialogue history shown to the LLM
Track 2 (Context): Rich background information injected separately

The two-track system allows Eva to maintain perfect memory without
cluttering conversations with context injection.
"""

from app.memory.conversation_track import ConversationHistory
from app.memory.context_track import ContextManager
from app.memory.retrieval import MemoryRetrieval

__all__ = [
    "ConversationHistory",
    "ContextManager",
    "MemoryRetrieval",
]
