"""Schemas for password reset."""
from pydantic import BaseModel, EmailStr, Field


class RequestPasswordResetRequest(BaseModel):
    """Request to initiate password reset."""
    email: EmailStr


class RequestPasswordResetResponse(BaseModel):
    """Response after requesting password reset."""
    message: str
    expires_in_minutes: int = 10


class VerifyPasswordResetRequest(BaseModel):
    """Request to verify password reset code."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class VerifyPasswordResetResponse(BaseModel):
    """Response after verifying password reset code."""
    verified: bool
    message: str
    reset_token: str  # Temporary token to allow password reset


class ResetPasswordRequest(BaseModel):
    """Request to reset password."""
    email: EmailStr
    reset_token: str
    new_password: str = Field(..., min_length=8, description="New password")


class ResetPasswordResponse(BaseModel):
    """Response after resetting password."""
    message: str
