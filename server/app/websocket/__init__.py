"""
WebSocket package for real-time conversation with Eva.

Provides:
- ConnectionManager: Track and manage WebSocket connections
- MessageProtocol: Validate and format WebSocket messages
- SessionManager: Manage WebSocket session state with Redis
"""

from app.websocket.connection_manager import ConnectionManager
from app.websocket.message_protocol import (
    ClientMessage,
    MessageType,
    format_response_chunk,
    format_error,
    format_system_event,
)

__all__ = [
    "ConnectionManager",
    "ClientMessage",
    "MessageType",
    "format_response_chunk",
    "format_error",
    "format_system_event",
]
