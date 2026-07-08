"""ResearchCache model for PostgreSQL-backed research result deduplication."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from src.models.base import Base


class ResearchCache(Base):
    """Maps to research_cache table (migration 020).

    Provides a durable PostgreSQL layer for research result deduplication
    alongside the primary Redis cache.  Useful for auditability and as a
    fallback when Redis data is evicted.
    """

    __tablename__ = "research_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dedupe_key = Column(String(64), nullable=False, unique=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    category = Column(String, nullable=False)
    job_type = Column(String, nullable=False, default="URL_DISCOVERY")
    latest_result_json = Column(JSONB, nullable=False, default=dict)
    citations_json = Column(JSONB, nullable=False, default=list)
    provider_name = Column(String, nullable=True)
    cost_usd = Column(Numeric(8, 4), nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
