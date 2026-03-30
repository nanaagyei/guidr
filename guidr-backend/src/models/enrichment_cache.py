"""EnrichmentCache model for shared cached enrichment results."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from src.models.base import Base


class EnrichmentCache(Base):
    """Maps to enrichment_cache table (migration 014).

    Caches aggregated enrichment results per entity with confidence scoring
    and expiration. Hit counting enables cache analytics.

    user_id (migration 017): NULL = global/shared entry; non-null = per-user dossier.
    """

    __tablename__ = "enrichment_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_kind = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    # NULL means the cache entry is global (shared); non-null scopes to one user
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    schema_version = Column(String, nullable=False, default="v1")
    freshness_bucket = Column(String, nullable=False, default="30d")

    value_json = Column(JSON, nullable=False)
    confidence = Column(Numeric(4, 3), nullable=True)

    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    source_extraction_run_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    citations_json = Column(JSON, nullable=False, default=list)
    evidence_map_json = Column(JSON, nullable=False, default=dict)

    hit_count = Column(Integer, nullable=False, default=0)
    last_hit_at = Column(DateTime, nullable=True)
