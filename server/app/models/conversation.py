"""
Conversation models - Track 1 (clean dialogue history).
Stores natural conversation flow without context pollution.
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class MessageRole(str, enum.Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"  # For system messages (rare, only for special cases)


class Conversation(Base):
    """
    Conversation session - a series of exchanges between user and character.
    Each conversation has its own character state.
    """
    __tablename__ = "conversations"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_state_id = Column(UUID(as_uuid=True), ForeignKey("character_states.id"), nullable=False)

    # Metadata
    title = Column(String(500), nullable=True)  # Auto-generated or user-provided
    platform = Column(String(50), nullable=True)  # "flutter", "discord", "terminal", etc.

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="conversations")
    character_state = relationship("CharacterState", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationTurn.timestamp")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class ConversationTurn(Base):
    """
    Individual message in a conversation - Track 1 (clean dialogue).
    This is what gets shown in the conversation - natural and clean.
    """
    __tablename__ = "conversation_turns"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Message data
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # Sequence number for ordering within conversation
    sequence = Column(Integer, nullable=False)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="turns")

    def __repr__(self):
        return f"<ConversationTurn(id={self.id}, role={self.role}, sequence={self.sequence})>"
