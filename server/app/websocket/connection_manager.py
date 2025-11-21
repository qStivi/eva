"""
WebSocket connection manager.

Handles connection lifecycle, tracking, and message sending for WebSocket clients.
"""

import logging
import uuid
from typing import Dict, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active WebSocket connections.

    Provides connection tracking, message sending helpers, and cleanup functionality.
    Each connection is assigned a unique ID for tracking.
    """

    def __init__(self):
        """Initialize connection manager with empty connection pool."""
        self.active_connections: Dict[str, WebSocket] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: The FastAPI WebSocket instance
            user_id: User ID associated with this connection

        Returns:
            str: Unique connection ID for this session
        """
        await websocket.accept()

        # Generate unique connection ID
        connection_id = str(uuid.uuid4())

        # Register connection
        self.active_connections[connection_id] = websocket

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        return connection_id

    async def disconnect(self, connection_id: str):
        """
        Disconnect and cleanup a WebSocket connection.

        Args:
            connection_id: The connection ID to disconnect
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocket]:
        """
        Get WebSocket instance for a connection ID.

        Args:
            connection_id: The connection ID

        Returns:
            WebSocket instance or None if not found
        """
        return self.active_connections.get(connection_id)

    async def send_json(self, connection_id: str, data: dict) -> bool:
        """
        Send JSON message to a specific connection.

        Args:
            connection_id: Target connection ID
            data: Dictionary to send as JSON

        Returns:
            bool: True if sent successfully, False if connection dead
        """
        websocket = self.get_connection(connection_id)
        if not websocket:
            logger.warning(f"Attempted to send to non-existent connection: {connection_id}")
            return False

        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending JSON to {connection_id}: {e}")
            await self.disconnect(connection_id)
            return False

    async def send_stream_chunk(
        self,
        connection_id: str,
        chunk: str,
        done: bool,
        **kwargs
    ) -> bool:
        """
        Send a streaming response chunk to a connection.

        Helper method that formats and sends response chunks using the
        standard protocol format.

        Args:
            connection_id: Target connection ID
            chunk: Text content to send
            done: Whether this is the final chunk
            **kwargs: Additional metadata (chunk_index, total_chunks, etc.)

        Returns:
            bool: True if sent successfully, False if connection dead
        """
        from app.websocket.message_protocol import format_response_chunk

        message = format_response_chunk(chunk, done, **kwargs)
        return await self.send_json(connection_id, message)

    def get_active_connection_count(self) -> int:
        """
        Get count of active connections.

        Returns:
            int: Number of active connections
        """
        return len(self.active_connections)

    def get_connection_ids(self) -> list[str]:
        """
        Get list of all active connection IDs.

        Returns:
            List of connection ID strings
        """
        return list(self.active_connections.keys())
