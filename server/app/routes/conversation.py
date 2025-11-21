"""
WebSocket conversation endpoint.

Real-time conversation with Eva via WebSocket with streaming responses.
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import ValidationError

from app.config import settings
from app.database import AsyncSessionLocal
from app.websocket.connection_manager import ConnectionManager
from app.websocket.session_manager import WebSocketSessionManager
from app.websocket.message_protocol import (
    ClientMessage,
    MessageType,
    ErrorCode,
    SystemEvent,
    format_response_chunk,
    format_error,
    format_system_event,
)
from app.llm.inference import generate_with_memory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Global managers (singleton pattern)
connection_manager = ConnectionManager()
session_manager = WebSocketSessionManager()


def authenticate_token(token: Optional[str]) -> Optional[str]:
    """
    Simple token authentication for MVP.

    Validates token against SECRET_KEY from config.
    Returns username if valid, None otherwise.

    Args:
        token: Authentication token from query parameter

    Returns:
        Username if authenticated, None otherwise
    """
    if token and token == settings.secret_key:
        # Return hardcoded user for MVP
        return "qStivi"
    return None


@router.websocket("/conversation")
async def websocket_conversation(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, description="Authentication token")
):
    """
    WebSocket endpoint for real-time conversation with streaming.

    Protocol:
    1. Client connects with ?token=SECRET_KEY
    2. Server authenticates and initializes session
    3. Server sends welcome message (type: system, event: connected)
    4. Client sends messages (type: message, content: "text")
    5. Server streams responses (type: response_chunk, done: false/true)
    6. Repeat step 4-5 for ongoing conversation
    7. Client disconnects or connection drops

    Query Parameters:
        token: Authentication token (must match SECRET_KEY)

    Client Message Format:
        {
            "type": "message",
            "content": "Hello Eva!",
            "metadata": {"timestamp": "2025-11-21T10:30:00Z"}
        }

    Server Response Formats:
        Stream chunk: {
            "type": "response_chunk",
            "content": "Hey",
            "done": false,
            "metadata": {"chunk_index": 0}
        }

        End signal: {
            "type": "response_chunk",
            "content": "",
            "done": true,
            "metadata": {"total_chunks": 42}
        }

        Error: {
            "type": "error",
            "code": "GENERATION_FAILED",
            "message": "An error occurred",
            "recoverable": true
        }
    """
    connection_id = None

    try:
        # Accept connection
        await websocket.accept()
        logger.info("WebSocket connection accepted, authenticating...")

        # Authenticate
        username = authenticate_token(token)
        if not username:
            logger.warning("WebSocket authentication failed")
            await websocket.send_json(format_error(
                ErrorCode.AUTH_FAILED,
                "Authentication failed. Invalid or missing token.",
                recoverable=False
            ))
            await websocket.close(code=1008)  # Policy violation
            return

        logger.info(f"WebSocket authenticated: user={username}")

        # Register connection
        connection_id = await connection_manager.connect(websocket, username)

        # Initialize session (load/create user, conversation, character state)
        async with AsyncSessionLocal() as db_session:
            session_data = await session_manager.create_session(
                connection_id, db_session
            )

        # Send welcome message
        await websocket.send_json(format_system_event(
            SystemEvent.CONNECTED,
            {
                "conversation_id": session_data["conversation_id"],
                "character_name": settings.character_name,
                "username": session_data["username"],
                "display_name": session_data["display_name"],
            }
        ))
        logger.info(f"WebSocket session initialized: {connection_id}")

        # Message loop
        while True:
            # Receive message from client
            raw_message = await websocket.receive_json()

            # Update activity timestamp
            await session_manager.update_activity(connection_id)

            # Validate and parse message
            try:
                client_message = ClientMessage(**raw_message)
            except ValidationError as e:
                logger.warning(f"Invalid message format: {e}")
                await websocket.send_json(format_error(
                    ErrorCode.INVALID_MESSAGE,
                    "Invalid message format. Check message structure.",
                    recoverable=True
                ))
                continue

            # Route message based on type
            if client_message.type == MessageType.MESSAGE:
                await handle_conversation_message(
                    websocket, connection_id, client_message, session_data
                )
            else:
                # Unknown message type
                logger.warning(f"Unknown message type: {client_message.type}")
                await websocket.send_json(format_error(
                    ErrorCode.INVALID_MESSAGE,
                    f"Unknown message type: {client_message.type}",
                    recoverable=True
                ))

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")

    except Exception as e:
        # Sanitize error message (never send internal details to client)
        logger.error(f"WebSocket error: {e}", exc_info=True)

        if connection_id:
            try:
                await websocket.send_json(format_error(
                    ErrorCode.INTERNAL_ERROR,
                    "An internal error occurred. Please try reconnecting.",
                    recoverable=False
                ))
            except Exception:
                # Connection already dead, can't send error
                pass

    finally:
        # Cleanup
        if connection_id:
            await connection_manager.disconnect(connection_id)
            await session_manager.end_session(connection_id)
            logger.info(f"WebSocket cleanup complete: {connection_id}")


async def handle_conversation_message(
    websocket: WebSocket,
    connection_id: str,
    message: ClientMessage,
    session_data: dict,
):
    """
    Handle user conversation message with streaming response.

    Generates response using two-track memory system and streams
    chunks to client as they're generated.

    Args:
        websocket: WebSocket connection
        connection_id: Connection ID
        message: Validated client message
        session_data: Session data from Redis
    """
    start_time = time.time()

    try:
        # Send thinking status
        await websocket.send_json(format_system_event(
            SystemEvent.THINKING,
            {"status": "Retrieving memories..."}
        ))

        # Generate response with memory integration (reuse terminal logic!)
        async with AsyncSessionLocal() as db_session:
            response_iterator = await generate_with_memory(
                session=db_session,
                user_id=session_data["user_id"],
                conversation_id=session_data["conversation_id"],
                user_message=message.content,
                character_state_id=session_data["character_state_id"],
                stream=True,  # Enable streaming
                # Debug flags always off for WebSocket (use server logs)
                debug_memory=False,
                debug_prompt=False,
                debug_llm=False,
            )

            # Stream chunks to client
            chunk_index = 0
            full_response = ""

            async for chunk in response_iterator:
                # Accumulate full response for logging
                full_response += chunk

                # Send chunk to client
                await websocket.send_json(format_response_chunk(
                    content=chunk,
                    done=False,
                    chunk_index=chunk_index
                ))
                chunk_index += 1

            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Send done signal
            await websocket.send_json(format_response_chunk(
                content="",
                done=True,
                total_chunks=chunk_index,
                generation_time_ms=generation_time_ms
            ))

            logger.info(
                f"Response generated: {connection_id} "
                f"({chunk_index} chunks, {generation_time_ms}ms)"
            )

    except Exception as e:
        # Sanitize error message
        logger.error(f"Error generating response: {e}", exc_info=True)

        await websocket.send_json(format_error(
            ErrorCode.GENERATION_FAILED,
            "Failed to generate response. Please try again.",
            recoverable=True
        ))
