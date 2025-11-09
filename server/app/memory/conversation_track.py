"""
Track 1: Conversation History

Manages clean dialogue history for the LLM. This track contains only
the actual conversation turns (user and assistant messages) without
any injected context or metadata.

Key features:
- Load conversation history from database
- Format messages for LLM context window
- Sliding window to keep recent N turns
- Conversation summarization for older messages
"""

from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, ConversationTurn
from app.models.conversation import MessageRole


class ConversationHistory:
    """
    Manages Track 1: Clean conversation history.
    
    This class handles loading, formatting, and windowing of conversation
    history to fit within the LLM's context window while maintaining
    conversation quality.
    """
    
    def __init__(
        self,
        max_turns: int = 20,
        include_system_prompt: bool = True,
    ):
        """
        Initialize conversation history manager.
        
        Args:
            max_turns: Maximum number of recent turns to include (sliding window)
            include_system_prompt: Whether to include system prompt in formatted output
        """
        self.max_turns = max_turns
        self.include_system_prompt = include_system_prompt
    
    async def load_history(
        self,
        session: AsyncSession,
        conversation_id: int,
        max_turns: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """
        Load conversation history from database.
        
        Args:
            session: Database session
            conversation_id: ID of the conversation
            max_turns: Override max_turns for this load
            
        Returns:
            List of conversation turns, ordered by sequence
        """
        turns_to_load = max_turns if max_turns is not None else self.max_turns
        
        # Load most recent turns, ordered by sequence
        query = (
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conversation_id)
            .order_by(ConversationTurn.sequence.desc())
            .limit(turns_to_load)
        )
        
        result = await session.execute(query)
        turns = result.scalars().all()
        
        # Reverse to get chronological order
        return list(reversed(turns))
    
    def format_for_llm(
        self,
        turns: List[ConversationTurn],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Format conversation turns for LLM input.
        
        Args:
            turns: List of conversation turns
            system_prompt: Optional system prompt to include
            
        Returns:
            List of message dicts with 'role' and 'content' keys
            Format: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        messages = []
        
        # Add system prompt if provided and enabled
        if self.include_system_prompt and system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })
        
        # Add conversation turns
        for turn in turns:
            messages.append({
                "role": turn.role.value,  # MessageRole enum to string
                "content": turn.content,
            })
        
        return messages
    
    async def save_turn(
        self,
        session: AsyncSession,
        conversation_id: int,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> ConversationTurn:
        """
        Save a new conversation turn to database.
        
        Args:
            session: Database session
            conversation_id: ID of the conversation
            role: Message role (USER or ASSISTANT)
            content: Message content
            metadata: Optional metadata for the turn
            
        Returns:
            Created ConversationTurn object
        """
        # Get next sequence number
        query = (
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conversation_id)
            .order_by(ConversationTurn.sequence.desc())
            .limit(1)
        )
        result = await session.execute(query)
        last_turn = result.scalar_one_or_none()
        
        next_sequence = (last_turn.sequence + 1) if last_turn else 0
        
        # Create new turn
        turn = ConversationTurn(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence=next_sequence,
            metadata=metadata or {},
        )
        
        session.add(turn)
        await session.commit()
        await session.refresh(turn)
        
        return turn
    
    def create_sliding_window(
        self,
        turns: List[ConversationTurn],
        max_turns: Optional[int] = None,
    ) -> List[ConversationTurn]:
        """
        Apply sliding window to conversation history.
        
        Keeps only the most recent N turns. Older turns can be
        summarized separately if needed.
        
        Args:
            turns: Full conversation history
            max_turns: Maximum turns to keep (overrides self.max_turns)
            
        Returns:
            Recent turns within the window
        """
        window_size = max_turns if max_turns is not None else self.max_turns
        
        if len(turns) <= window_size:
            return turns
        
        # Keep most recent turns
        return turns[-window_size:]
    
    async def get_conversation_metadata(
        self,
        session: AsyncSession,
        conversation_id: int,
    ) -> Dict:
        """
        Get metadata about a conversation.
        
        Args:
            session: Database session
            conversation_id: ID of the conversation
            
        Returns:
            Dict with conversation metadata (turn count, duration, etc.)
        """
        # Load conversation
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one()
        
        # Count turns
        result = await session.execute(
            select(ConversationTurn)
            .where(ConversationTurn.conversation_id == conversation_id)
        )
        turns = result.scalars().all()
        
        # Calculate metadata
        metadata = {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "platform": conversation.platform,
            "started_at": conversation.started_at,  # Fixed: was created_at
            "ended_at": conversation.ended_at,
            "updated_at": conversation.updated_at,
            "total_turns": len(turns),
            "user_turns": sum(1 for t in turns if t.role == MessageRole.USER),
            "assistant_turns": sum(1 for t in turns if t.role == MessageRole.ASSISTANT),
        }

        return metadata
    
    def format_history_as_text(
        self,
        turns: List[ConversationTurn],
    ) -> str:
        """
        Format conversation history as readable text.
        
        Useful for summarization or logging.
        
        Args:
            turns: List of conversation turns
            
        Returns:
            Formatted text representation
        """
        lines = []
        for turn in turns:
            role_label = "You" if turn.role == MessageRole.USER else "Eva"
            timestamp = turn.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[{timestamp}] {role_label}: {turn.content}")
        
        return "\n".join(lines)
