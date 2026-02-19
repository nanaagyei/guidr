"""Authentication schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str
    verification_code: Optional[str] = None  # 2FA code for final registration step


class UserLogin(BaseModel):
    """User login schema."""
    email: EmailStr
    password: str
    verification_code: Optional[str] = None  # 2FA code for login verification
    remember_me: bool = False


class VerifyCredentialsRequest(BaseModel):
    """Request to verify user credentials before sending 2FA code."""
    email: EmailStr
    password: str


class VerifyCredentialsResponse(BaseModel):
    """Response after verifying credentials."""
    verified: bool
    message: str


class CheckEmailRequest(BaseModel):
    """Request to check if an email is already registered."""
    email: EmailStr


class CheckEmailResponse(BaseModel):
    """Response indicating whether an email exists."""
    exists: bool
    message: str


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    full_name: str
    role: str
    created_at: str
