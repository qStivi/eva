"""
CharacterState model - Eva's internal state and personality.
Tracks mood, preferences, and future goals/desires.
"""
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CharacterState(Base):
    """
    Character state model - represents Eva's internal state.
    One state per conversation, tracks mood and personality evolution.
    """
    __tablename__ = "character_states"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Mood tracking
    # Example: "curious", "playful", "thoughtful", "concerned", "excited"
    mood = Column(String(50), nullable=False, default="neutral")

    # Mood context - why is the character in this mood?
    mood_context = Column(Text, nullable=True)

    # Character preferences (JSON)
    # Example: {"communication_style": "casual", "topics_of_interest": ["tech", "art"], ...}
    preferences = Column(JSON, default=dict, nullable=False)

    # Goals and desires (JSON) - for Phase 6+
    # Example: {"current_goals": ["understand user's project", "help with journaling"], ...}
    goals = Column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="character_state")

    def __repr__(self):
        return f"<CharacterState(id={self.id}, mood={self.mood})>"
