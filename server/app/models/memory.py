"""
Memory model - Track 2 (side context injection).
Links PostgreSQL metadata to ChromaDB vector embeddings for semantic search.
"""
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Memory(Base):
    """
    Memory model - metadata for context injection (Track 2).
    Stores summaries and links to ChromaDB vectors for semantic search.
    """
    __tablename__ = "memories"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)

    # ChromaDB reference
    embedding_id = Column(String(255), nullable=False, index=True)  # ID in ChromaDB collection

    # Memory content
    content_summary = Column(Text, nullable=False)  # Human-readable summary
    full_content = Column(Text, nullable=True)  # Optional full content for reference

    # Metadata
    memory_type = Column(String(50), nullable=False, default="conversation")  # "conversation", "event", "preference", etc.
    tags = Column(String(1000), nullable=True)  # Comma-separated tags for filtering

    # Importance scoring
    importance_score = Column(Float, nullable=False, default=0.5)  # 0.0 to 1.0

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    accessed_at = Column(DateTime(timezone=True), nullable=True)  # Last time this memory was retrieved

    # Relationships
    user = relationship("User", back_populates="memories")

    def __repr__(self):
        return f"<Memory(id={self.id}, type={self.memory_type}, importance={self.importance_score})>"
