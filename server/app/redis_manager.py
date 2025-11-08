"""
Redis session manager for temporary state and caching.
Handles active conversations, session data, and frequently accessed context.
"""
import redis.asyncio as redis
from typing import Optional, Dict, Any
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis manager for session state and caching.

    Key patterns:
    - session:{user_id}:{conversation_id} - Active conversation state
    - user:{user_id}:active_conversation - Current active conversation ID
    - cache:{type}:{id} - Cached data (e.g., recently accessed memories)
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis server."""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        """Check if Redis is accessible."""
        try:
            if self.redis_client:
                return await self.redis_client.ping()
            return False
        except Exception:
            return False

    # Session Management

    async def set_session_data(
        self, user_id: str, conversation_id: str, data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """
        Store session data for a conversation.

        Args:
            user_id: User ID
            conversation_id: Conversation ID
            data: Session data to store
            ttl: Time-to-live in seconds (default 1 hour)

        Returns:
            True if successful
        """
        try:
            key = f"session:{user_id}:{conversation_id}"
            await self.redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to set session data: {e}")
            return False

    async def get_session_data(
        self, user_id: str, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data for a conversation.

        Args:
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            Session data dict or None if not found
        """
        try:
            key = f"session:{user_id}:{conversation_id}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get session data: {e}")
            return None

    async def delete_session_data(self, user_id: str, conversation_id: str) -> bool:
        """Delete session data for a conversation."""
        try:
            key = f"session:{user_id}:{conversation_id}"
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete session data: {e}")
            return False

    # Active Conversation Tracking

    async def set_active_conversation(
        self, user_id: str, conversation_id: str
    ) -> bool:
        """
        Set the user's currently active conversation.

        Args:
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            True if successful
        """
        try:
            key = f"user:{user_id}:active_conversation"
            await self.redis_client.set(key, conversation_id)
            return True
        except Exception as e:
            logger.error(f"Failed to set active conversation: {e}")
            return False

    async def get_active_conversation(self, user_id: str) -> Optional[str]:
        """
        Get the user's currently active conversation ID.

        Args:
            user_id: User ID

        Returns:
            Conversation ID or None
        """
        try:
            key = f"user:{user_id}:active_conversation"
            return await self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Failed to get active conversation: {e}")
            return None

    async def clear_active_conversation(self, user_id: str) -> bool:
        """Clear the user's active conversation."""
        try:
            key = f"user:{user_id}:active_conversation"
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear active conversation: {e}")
            return False

    # Caching

    async def set_cache(
        self, cache_type: str, item_id: str, data: Dict[str, Any], ttl: int = 300
    ) -> bool:
        """
        Store data in cache.

        Args:
            cache_type: Type of cached data (e.g., "memory", "character_state")
            item_id: Item identifier
            data: Data to cache
            ttl: Time-to-live in seconds (default 5 minutes)

        Returns:
            True if successful
        """
        try:
            key = f"cache:{cache_type}:{item_id}"
            await self.redis_client.setex(key, ttl, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False

    async def get_cache(
        self, cache_type: str, item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from cache.

        Args:
            cache_type: Type of cached data
            item_id: Item identifier

        Returns:
            Cached data or None if not found/expired
        """
        try:
            key = f"cache:{cache_type}:{item_id}"
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache: {e}")
            return None

    async def invalidate_cache(self, cache_type: str, item_id: str) -> bool:
        """Invalidate cached data."""
        try:
            key = f"cache:{cache_type}:{item_id}"
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return False

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """
        Invalidate all cached data matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "cache:memory:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern: {e}")
            return 0


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> RedisManager:
    """
    Dependency for FastAPI routes to get Redis manager.

    Usage:
        @app.get("/endpoint")
        async def endpoint(redis: RedisManager = Depends(get_redis)):
            # Use redis here
    """
    return redis_manager
