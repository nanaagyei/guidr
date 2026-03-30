"""SavedRecommendation model for tracking user-saved recommendations and deep research jobs."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class SavedRecommendation(Base):
    """Tracks when a user saves a recommended school and the research jobs triggered."""

    __tablename__ = "saved_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recommendation_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Materialized when user saves — may be NULL initially
    institution_id = Column(UUID(as_uuid=True), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id", ondelete="SET NULL"), nullable=True)

    # Pipeline job references for deep research
    school_dossier_job_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True)
    professor_match_job_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True)
    funding_dossier_job_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True)

    research_status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="saved_recommendations")
    recommendation_result = relationship("RecommendationResult", backref="saved_recommendation")
    institution = relationship("Institution", backref="saved_recommendations")
    program = relationship("Program", backref="saved_recommendations")
