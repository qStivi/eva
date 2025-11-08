"""
Track 2: Context Injection

Manages side context that's injected separately from the conversation history.
This track contains rich background information, user preferences, retrieved
memories, and environmental context.

Key features:
- Build comprehensive context from multiple sources
- Format retrieved memories for LLM injection
- Include user preferences and character state
- Add temporal context (time, date, day of week)
- Support for external triggers (webhooks, Phase 5+)
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.character import CharacterState


class ContextManager:
    """
    Manages Track 2: Side context injection.

    This class builds the rich background context that gets injected
    separately from the clean conversation history. This prevents
    duplication and keeps the conversation natural while maintaining
    perfect memory.
    """

    def __init__(
        self,
        include_temporal: bool = True,
        include_preferences: bool = True,
        include_character_state: bool = True,
    ):
        """
        Initialize context manager.

        Args:
            include_temporal: Include time/date context
            include_preferences: Include user preferences
            include_character_state: Include character mood/state
        """
        self.include_temporal = include_temporal
        self.include_preferences = include_preferences
        self.include_character_state = include_character_state

    async def build_context(
        self,
        session: AsyncSession,
        user_id: str,
        character_state_id: Optional[str] = None,
        retrieved_memories: Optional[List[Dict[str, Any]]] = None,
        external_triggers: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Build complete context string for LLM injection.

        This is the main entry point that orchestrates all context sources
        and formats them into a coherent context block.

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            character_state_id: Optional character state ID (UUID as string)
            retrieved_memories: Optional list of memories from semantic search
            external_triggers: Optional list of external events (Phase 5+)

        Returns:
            Formatted context string ready for injection
        """
        context_parts = []

        # 1. Temporal context (time, date, day of week)
        if self.include_temporal:
            temporal_context = self.format_temporal_context()
            if temporal_context:
                context_parts.append(temporal_context)

        # 2. User preferences
        if self.include_preferences:
            user_prefs = await self.get_user_preferences(session, user_id)
            if user_prefs:
                context_parts.append(user_prefs)

        # 3. Character state (mood, preferences)
        if self.include_character_state and character_state_id:
            char_state = await self.get_character_state(session, character_state_id)
            if char_state:
                context_parts.append(char_state)

        # 4. Retrieved memories (Track 2 semantic search results)
        if retrieved_memories:
            memories_context = self.format_memories(retrieved_memories)
            if memories_context:
                context_parts.append(memories_context)

        # 5. External triggers (webhooks, Phase 5+)
        if external_triggers:
            triggers_context = self.format_external_triggers(external_triggers)
            if triggers_context:
                context_parts.append(triggers_context)

        # Combine all context parts
        if not context_parts:
            return ""

        # Format as a coherent context block
        context = "\n\n".join(context_parts)
        return f"[Context and Background Information]\n\n{context}"

    async def get_user_preferences(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> Optional[str]:
        """
        Load user preferences from database and format for context.

        Args:
            session: Database session
            user_id: User ID (UUID as string)

        Returns:
            Formatted user preferences string, or None if no preferences
        """
        # Load user from database
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.preferences:
            return None

        # Format preferences
        prefs = user.preferences

        # Build preferences text
        pref_lines = []

        # Add display name if available
        if user.display_name:
            pref_lines.append(f"User prefers to be called: {user.display_name}")

        # Add user preferences from JSON
        if prefs:
            for key, value in prefs.items():
                # Convert snake_case to readable format
                readable_key = key.replace("_", " ").title()
                pref_lines.append(f"{readable_key}: {value}")

        if not pref_lines:
            return None

        return "User Preferences:\n" + "\n".join(f"- {line}" for line in pref_lines)

    async def get_character_state(
        self,
        session: AsyncSession,
        character_state_id: str,
    ) -> Optional[str]:
        """
        Load character state (mood, preferences, goals) from database.

        Args:
            session: Database session
            character_state_id: Character state ID (UUID as string)

        Returns:
            Formatted character state string, or None if not found
        """
        # Load character state from database
        result = await session.execute(
            select(CharacterState).where(CharacterState.id == character_state_id)
        )
        character_state = result.scalar_one_or_none()

        if not character_state:
            return None

        # Build character state text
        state_lines = []

        # Add mood
        if character_state.mood and character_state.mood != "neutral":
            state_lines.append(f"Current mood: {character_state.mood}")

            # Add mood context if available
            if character_state.mood_context:
                state_lines.append(f"Mood context: {character_state.mood_context}")

        # Add character preferences
        if character_state.preferences:
            for key, value in character_state.preferences.items():
                readable_key = key.replace("_", " ").title()
                state_lines.append(f"{readable_key}: {value}")

        # Add goals (Phase 6+, might be empty for now)
        if character_state.goals:
            goals = character_state.goals
            if goals:
                state_lines.append("Active goals:")
                for goal_key, goal_value in goals.items():
                    state_lines.append(f"  - {goal_key}: {goal_value}")

        if not state_lines:
            return None

        return "Character State (Internal):\n" + "\n".join(f"- {line}" for line in state_lines)

    def format_temporal_context(self) -> str:
        """
        Generate temporal context (current time, date, day of week).

        This helps the character be aware of time-sensitive information
        like "good morning" vs "good evening", day of the week, etc.

        Returns:
            Formatted temporal context string
        """
        now = datetime.now(timezone.utc)

        # Day of week
        day_name = now.strftime("%A")

        # Date
        date_str = now.strftime("%B %d, %Y")

        # Time of day
        hour = now.hour
        if 5 <= hour < 12:
            time_of_day = "morning"
        elif 12 <= hour < 17:
            time_of_day = "afternoon"
        elif 17 <= hour < 21:
            time_of_day = "evening"
        else:
            time_of_day = "night"

        # Format
        return f"Current Time: {day_name}, {date_str} ({time_of_day})"

    def format_memories(
        self,
        memories: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Format retrieved memories for context injection.

        Takes memories from semantic search (ChromaDB) and formats them
        in a way that's natural for the LLM to use.

        Args:
            memories: List of memory dicts with keys:
                - content_summary: The memory content
                - importance_score: Importance score (0.0-1.0)
                - created_at: When the memory was created
                - metadata: Additional metadata

        Returns:
            Formatted memories string, or None if no memories
        """
        if not memories:
            return None

        # Sort by importance score (highest first)
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get("importance_score", 0.5),
            reverse=True,
        )

        # Format memories
        memory_lines = []
        for i, memory in enumerate(sorted_memories, 1):
            content = memory.get("content_summary", memory.get("content", ""))
            importance = memory.get("importance_score", 0.5)

            # Add importance indicator for high-importance memories
            importance_marker = ""
            if importance >= 0.8:
                importance_marker = " [important]"
            elif importance >= 0.6:
                importance_marker = " [notable]"

            memory_lines.append(f"{i}. {content}{importance_marker}")

        return "Relevant Memories:\n" + "\n".join(memory_lines)

    def format_external_triggers(
        self,
        triggers: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Format external triggers (webhooks, integrations) for context.

        Phase 5+ feature for external events like:
        - Home Assistant events ("User arrived home")
        - Calendar events ("Meeting in 30 minutes")
        - IFTTT triggers ("User posted on social media")

        Args:
            triggers: List of trigger dicts with keys:
                - source: Trigger source (e.g., "home_assistant")
                - event_type: Type of event (e.g., "arrival")
                - description: Human-readable description
                - timestamp: When the trigger occurred

        Returns:
            Formatted triggers string, or None if no triggers
        """
        if not triggers:
            return None

        # Sort by timestamp (most recent first)
        sorted_triggers = sorted(
            triggers,
            key=lambda t: t.get("timestamp", datetime.min),
            reverse=True,
        )

        # Format triggers
        trigger_lines = []
        for trigger in sorted_triggers:
            source = trigger.get("source", "unknown")
            description = trigger.get("description", "")
            trigger_lines.append(f"[{source}] {description}")

        return "Recent Events:\n" + "\n".join(f"- {line}" for line in trigger_lines)

    def combine_with_system_prompt(
        self,
        system_prompt: str,
        context: str,
    ) -> str:
        """
        Combine system prompt with context injection.

        This is a helper method for creating the final system message
        that includes both the character prompt and the context.

        Args:
            system_prompt: Eva's character prompt
            context: Built context from build_context()

        Returns:
            Combined system prompt with context
        """
        if not context:
            return system_prompt

        return f"{system_prompt}\n\n{context}"
