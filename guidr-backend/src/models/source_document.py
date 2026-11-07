"""SourceDocument model for canonical URLs per entity."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Computed, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# Values of the Postgres enum `research_provider` used by `discovered_by`.
RESEARCH_PROVIDERS = frozenset({"perplexity", "open_deep_research", "langchain_custom", "manual"})


def research_provider_label(source: str | None) -> str:
    """Map a provider's free-form result ``source`` onto the ``research_provider`` enum.

    Providers label results ``perplexity_sonar``, ``perplexity_citation``,
    ``open_deep_research`` and so on; inserting those raw values fails the enum.
    """
    value = (source or "").lower()
    if value in RESEARCH_PROVIDERS:
        return value
    if value.startswith("open_deep_research"):
        return "open_deep_research"
    if value.startswith("perplexity") and value != "perplexity_stub":
        return "perplexity"
    return "manual"


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

    # GENERATED ALWAYS in PostgreSQL. Declared as Computed so the ORM never sends a value
    # for them (an explicit NULL makes Postgres reject every insert).
    url_hash = Column(
        String,
        Computed("encode(digest(lower(canonical_url), 'sha256'), 'hex')", persisted=True),
        nullable=True,
    )
    host = Column(
        String,
        Computed(
            "split_part(replace(replace(canonical_url, 'https://', ''), 'http://', ''), '/', 1)",
            persisted=True,
        ),
        nullable=True,
    )

    purpose = Column(Text, nullable=True)
    discovered_by = Column(String, default="manual")  # perplexity, manual, etc.
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)
    last_crawled_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    # Relationships
    raw_artifacts = relationship("RawArtifact", back_populates="source_document")
