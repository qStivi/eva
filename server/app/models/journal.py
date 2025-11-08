"""
JournalEntry model - Logseq integration for journaling.
Eva naturally documents your life through journal entries.
"""
from sqlalchemy import Column, String, DateTime, Text, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class JournalEntry(Base):
    """
    Journal entry model - represents a Logseq journal entry.
    Links conversations to journal entries for context.
    """
    __tablename__ = "journal_entries"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Journal metadata
    date = Column(Date, nullable=False, index=True)  # The journal entry date
    title = Column(String(500), nullable=True)  # Optional title

    # Content
    content = Column(Text, nullable=False)  # The journal entry content (Markdown)

    # Conversation links
    # Array of conversation IDs that contributed to this entry
    conversation_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)

    # Logseq integration
    logseq_path = Column(String(1000), nullable=True)  # Path to the .md file in Logseq
    synced_to_logseq = Column(DateTime(timezone=True), nullable=True)  # Last sync time

    # Metadata
    tags = Column(String(1000), nullable=True)  # Comma-separated tags
    mood = Column(String(50), nullable=True)  # Mood at time of entry

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="journal_entries")

    def __repr__(self):
        return f"<JournalEntry(id={self.id}, date={self.date}, user_id={self.user_id})>"
