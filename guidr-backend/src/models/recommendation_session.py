"""RecommendationSession model for storing recommendation generation sessions."""
from sqlalchemy import Column, String, JSON, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base
import enum


class RecommendationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationSession(Base):
    """Recommendation session model for tracking recommendation generation."""

    __tablename__ = "recommendation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    trigger_source = Column(String, nullable=True)  # 'dashboard_button', 'profile_change', 'manual'
    input_profile_snapshot = Column(JSON, nullable=True)  # Store relevant profile fields for audit
    algorithm_version = Column(String, default="mvp_v1", nullable=False)

    # Use String column with enum validation to avoid PostgreSQL enum case issues
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )
    error_message = Column(String, nullable=True)

    pipeline_job_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_jobs.id", ondelete="SET NULL"), nullable=True)
    citations_json = Column(JSON, nullable=False, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="recommendation_sessions")
    results = relationship("RecommendationResult", back_populates="session", cascade="all, delete-orphan")

    @property
    def status_enum(self) -> RecommendationStatus:
        """Get status as enum."""
        return RecommendationStatus(self.status) if self.status else RecommendationStatus.PENDING

    @status_enum.setter
    def status_enum(self, value: RecommendationStatus):
        """Set status from enum."""
        self.status = value.value if isinstance(value, RecommendationStatus) else value
