"""DomainHealth model for per-domain error tracking."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from src.models.base import Base


class DomainHealth(Base):
    """Maps to domain_health table (migration 014).

    Tracks per-domain scraping health: error streaks, block detection,
    and cooldown windows for circuit-breaker logic.
    """

    __tablename__ = "domain_health"

    host = Column(String, primary_key=True)
    last_ok_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    error_streak = Column(Integer, nullable=False, default=0)
    block_detected = Column(Boolean, nullable=False, default=False)
    next_allowed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
