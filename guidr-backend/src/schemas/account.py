"""Schemas for account self-service routes."""
from pydantic import BaseModel, Field


class ChangePasswordRequest(BaseModel):
    """Change the password of the signed-in user."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=1)


class ChangePasswordResponse(BaseModel):
    """Response after a successful password change."""
    message: str


class DeleteAccountRequest(BaseModel):
    """Re-authentication for account deletion."""
    password: str = Field(..., min_length=1)
