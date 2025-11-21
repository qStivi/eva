"""
WebSocket message protocol.

Defines message formats, validation, and formatting utilities for WebSocket
communication between client and server.
"""

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


# Client → Server Message Types
class MessageType(str, Enum):
    """Types of messages clients can send."""
    MESSAGE = "message"  # User conversation message


# Server → Client Message Types
class ResponseType(str, Enum):
    """Types of messages server can send."""
    RESPONSE_CHUNK = "response_chunk"  # Streaming response chunk
    ERROR = "error"  # Error message
    SYSTEM = "system"  # System event (thinking, connected, etc.)
    CHARACTER_STATE = "character_state"  # Character mood/state update


# Client Message Models
class ClientMessage(BaseModel):
    """
    Base message from client.

    Validates all incoming WebSocket messages from clients.
    """
    type: MessageType = Field(..., description="Message type")
    content: str = Field(..., description="Message content (user's text)")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata (timestamp, client version, etc.)"
    )

    class Config:
        """Pydantic config."""
        use_enum_values = True


# Server Message Formatters
def format_response_chunk(
    content: str,
    done: bool,
    chunk_index: Optional[int] = None,
    total_chunks: Optional[int] = None,
    generation_time_ms: Optional[int] = None,
    **kwargs
) -> dict:
    """
    Format a streaming response chunk for client.

    Args:
        content: Text content of this chunk
        done: Whether this is the final chunk
        chunk_index: Optional index of this chunk
        total_chunks: Optional total number of chunks (only on final chunk)
        generation_time_ms: Optional generation time (only on final chunk)
        **kwargs: Additional metadata to include

    Returns:
        Formatted message dictionary
    """
    message = {
        "type": ResponseType.RESPONSE_CHUNK.value,
        "content": content,
        "done": done,
        "metadata": {}
    }

    # Add optional metadata
    if chunk_index is not None:
        message["metadata"]["chunk_index"] = chunk_index

    if done:
        if total_chunks is not None:
            message["metadata"]["total_chunks"] = total_chunks
        if generation_time_ms is not None:
            message["metadata"]["generation_time_ms"] = generation_time_ms

    # Add any additional kwargs to metadata
    message["metadata"].update(kwargs)

    return message


def format_error(
    code: str,
    message: str,
    recoverable: bool = True,
    **kwargs
) -> dict:
    """
    Format an error message for client.

    IMPORTANT: Always sanitize error messages. Never send stack traces
    or internal details to client for security reasons.

    Args:
        code: Error code (INVALID_MESSAGE, GENERATION_FAILED, etc.)
        message: User-friendly error description (sanitized!)
        recoverable: Whether client can continue or should disconnect
        **kwargs: Additional error metadata

    Returns:
        Formatted error message dictionary
    """
    error_msg = {
        "type": ResponseType.ERROR.value,
        "code": code,
        "message": message,
        "recoverable": recoverable,
    }

    # Add any additional metadata
    if kwargs:
        error_msg["metadata"] = kwargs

    return error_msg


def format_system_event(
    event: str,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> dict:
    """
    Format a system event message for client.

    System events include: connected, thinking, typing, etc.

    Args:
        event: Event name (connected, thinking, etc.)
        data: Optional event data
        **kwargs: Additional data fields

    Returns:
        Formatted system event message
    """
    message = {
        "type": ResponseType.SYSTEM.value,
        "event": event,
        "data": data or {}
    }

    # Add any additional kwargs to data
    message["data"].update(kwargs)

    return message


def format_character_state(
    mood: str,
    mood_context: Optional[str] = None,
    **kwargs
) -> dict:
    """
    Format a character state update message.

    Sent when Eva's mood or state changes during conversation.

    Args:
        mood: Current mood (curious, playful, thoughtful, etc.)
        mood_context: Optional context explaining the mood
        **kwargs: Additional state data

    Returns:
        Formatted character state message
    """
    message = {
        "type": ResponseType.CHARACTER_STATE.value,
        "mood": mood,
    }

    if mood_context:
        message["mood_context"] = mood_context

    # Add any additional kwargs
    message.update(kwargs)

    return message


# Error Code Constants
class ErrorCode:
    """Standard error codes for WebSocket communication."""
    AUTH_FAILED = "AUTH_FAILED"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    GENERATION_FAILED = "GENERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SESSION_ERROR = "SESSION_ERROR"
    RATE_LIMIT = "RATE_LIMIT"


# System Event Constants
class SystemEvent:
    """Standard system event names."""
    CONNECTED = "connected"
    THINKING = "thinking"
    RETRIEVING_MEMORIES = "retrieving_memories"
    GENERATING = "generating"
