"""Pydantic schemas for user profile."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from uuid import UUID


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


class UserProfileUpdate(UserProfileBase):
    """Schema for updating user profile."""
    pass


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response."""
    id: UUID
    user_id: UUID
    profile_completion_score: int
    
    model_config = ConfigDict(from_attributes=True)

