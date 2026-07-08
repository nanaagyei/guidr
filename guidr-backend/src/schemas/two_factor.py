"""Schemas for two-factor authentication."""
from pydantic import BaseModel, EmailStr, Field


class Send2FACodeRequest(BaseModel):
    """Request to send a 2FA code."""
    email: EmailStr
    purpose: str = Field(..., description="Purpose: 'register', 'login', or 'password_reset'")


class Send2FACodeResponse(BaseModel):
    """Response after sending 2FA code."""
    message: str
    expires_in_minutes: int = 10


class Verify2FACodeRequest(BaseModel):
    """Request to verify a 2FA code."""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    purpose: str = Field(..., description="Purpose: 'register', 'login', or 'password_reset'")


class Verify2FACodeResponse(BaseModel):
    """Response after verifying 2FA code."""
    verified: bool
    message: str
