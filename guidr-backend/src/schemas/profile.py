"""Pydantic schemas for user profile."""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from uuid import UUID

from src.utils.sanitization import normalize_string_list


class UserProfileBase(BaseModel):
    """Base schema for user profile."""
    country_of_citizenship: Optional[str] = None
    current_country: Optional[str] = None
    current_city: Optional[str] = None
    intended_degree: Optional[str] = None  # 'masters' or 'phd'
    primary_field_of_study: Optional[str] = None
    secondary_fields: Optional[List[str]] = None
    preferred_start_term: Optional[str] = None
    preferred_start_year: Optional[int] = None
    preferred_countries: Optional[List[str]] = None
    preferred_cities: Optional[List[str]] = None
    funding_priority: Optional[str] = None
    program_style_preference: Optional[str] = None
    research_areas: Optional[List[str]] = None
    career_goals: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    """Schema for updating user profile.

    Array fields accept either a list of strings or a single
    comma-separated string for backward compatibility.  Values are
    normalised: trimmed, deduplicated (case-insensitive), and capped.
    """

    @field_validator(
        "preferred_countries",
        "preferred_cities",
        "research_areas",
        "secondary_fields",
        mode="before",
    )
    @classmethod
    def normalize_list_fields(cls, v):
        if v is None:
            return None
        result = normalize_string_list(v, max_items=30, max_item_length=100)
        return result if result else None


class ProfileCompletionResponse(BaseModel):
    """Profile completion details with level-based unlocks."""
    percent: int
    level: int
    missing_fields: List[str]
    unlocks: dict


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response."""
    id: UUID
    user_id: UUID
    profile_completion_score: int
    completion: Optional[ProfileCompletionResponse] = None

    model_config = ConfigDict(from_attributes=True)
