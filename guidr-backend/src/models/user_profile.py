"""UserProfile model for user preferences and goals."""
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.models.base import Base


class UserProfile(Base):
    """User profile model for goals, preferences, and personalization data."""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Goals & identity
    country_of_citizenship = Column(String, nullable=True)
    current_country = Column(String, nullable=True)
    current_city = Column(String, nullable=True)
    intended_degree = Column(String, nullable=True)  # 'masters' or 'phd'
    primary_field_of_study = Column(String, nullable=True)
    secondary_fields = Column(JSON, nullable=True)  # Array of strings
    preferred_start_term = Column(String, nullable=True)  # e.g., 'fall'
    preferred_start_year = Column(Integer, nullable=True)

    # Preferences
    preferred_countries = Column(JSON, nullable=True)  # Array of country strings
    preferred_cities = Column(JSON, nullable=True)  # Array of city strings
    funding_priority = Column(String, nullable=True)  # 'must_have', 'nice_to_have', 'no_preference'
    program_style_preference = Column(String, nullable=True)  # 'research', 'coursework', 'both'

    # Research interests & goals (collected during onboarding)
    research_areas = Column(JSON, nullable=True)   # Array of research interest strings
    career_goals = Column(String, nullable=True)    # Free-text career goals

    # Completion & embeddings
    profile_completion_score = Column(Integer, default=0, nullable=False)  # 0-100
    profile_embedding = Column(JSON, nullable=True)  # Vector for semantic matching (future)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", backref="profile")
