"""SourceDocument model for canonical URLs per entity."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class SourceDocument(Base):
    """Maps to source_documents table (migration 014).

    Stores canonical URLs associated with entities. The url_hash and host
    columns are GENERATED ALWAYS in PostgreSQL; here they are mapped as
    server-computed (not set by the ORM, read-only after insert).
    """

    __tablename__ = "source_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_kind = Column(String, nullable=False)  # school, program, professor, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    canonical_url = Column(Text, nullable=False)

    # Generated columns in PostgreSQL -- read-only from ORM perspective
    url_hash = Column(String, nullable=True)
    host = Column(String, nullable=True)

    purpose = Column(Text, nullable=True)
    discovered_by = Column(String, default="manual")  # perplexity, manual, etc.
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    # Relationships
    raw_artifacts = relationship("RawArtifact", back_populates="source_document")
