"""Pydantic schemas for faculty/professor validation."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ResearchAreaCreate(BaseModel):
    """Validated research area tag."""

    tag_name: str = Field(..., min_length=1, max_length=200)


class ProfessorCreate(BaseModel):
    """Validated professor data ready for persistence."""

    full_name: str = Field(..., min_length=2, max_length=300)
    title: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = None
    personal_page_url: Optional[str] = None
    scholar_profile_url: Optional[str] = None
    research_summary: Optional[str] = None
    interests_tags: Optional[List[str]] = None
    is_accepting_students: Optional[bool] = None
