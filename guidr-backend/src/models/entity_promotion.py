"""EntityPromotion model for audit trail of data promotions."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class EntityPromotion(Base):
    """Maps to entity_promotions table (migration 014).

    Audit trail recording when extracted data is promoted to production tables.
    Stores the diff of changes applied and who/what triggered the promotion.
    """

    __tablename__ = "entity_promotions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_run_id = Column(UUID(as_uuid=True), ForeignKey("extraction_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_kind = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)

    promoted_by = Column(String, nullable=False, default="system")
    promoted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    promotion_notes = Column(Text, nullable=True)
    diff_json = Column(JSON, nullable=False, default=dict)

    # Relationships
    extraction_run = relationship("ExtractionRun", back_populates="promotions")
