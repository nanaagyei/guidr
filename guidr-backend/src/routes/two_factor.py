"""Two-factor authentication routes.

Email-code verification is used only for **registration** and **password reset**.
Login uses email + password directly (no email code required).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db import get_db
from src.schemas.two_factor import (
    Send2FACodeRequest,
    Send2FACodeResponse,
    Verify2FACodeRequest,
    Verify2FACodeResponse,
)
from src.utils.two_factor import create_2fa_code, verify_2fa_code
from src.services.email import send_2fa_code_email
from src.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/2fa", tags=["2fa"])

_ALLOWED_PURPOSES = {"register", "password_reset"}


@router.post("/send", response_model=Send2FACodeResponse)
async def send_2fa_code(
    request: Send2FACodeRequest,
    db: Session = Depends(get_db)
):
    """Send a 2FA verification code to the user's email.

    Only ``register`` and ``password_reset`` purposes are accepted.
    Login no longer requires an email verification code.
    """
    if request.purpose not in _ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purpose must be 'register' or 'password_reset'"
        )

    if request.purpose == "password_reset":
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_id = str(user.id)
    else:
        user_id = None

    from datetime import datetime, timedelta
    from src.models.two_factor_code import TwoFactorCode
    recent_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.email == request.email,
        TwoFactorCode.purpose == request.purpose,
        TwoFactorCode.created_at > datetime.utcnow() - timedelta(seconds=30)
    ).first()

    if recent_code:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code. A code was recently sent."
        )

    two_factor_code = create_2fa_code(
        db=db,
        user_id=user_id,
        email=request.email,
        purpose=request.purpose
    )

    email_sent = await send_2fa_code_email(
        to_email=request.email,
        code=two_factor_code.code,
        purpose=request.purpose
    )

    if not email_sent:
        two_factor_code.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )

    return Send2FACodeResponse(
        message="Verification code sent to your email",
        expires_in_minutes=10
    )


@router.post("/verify", response_model=Verify2FACodeResponse)
async def verify_2fa_code_endpoint(
    request: Verify2FACodeRequest,
    db: Session = Depends(get_db)
):
    """Verify a 2FA code.

    Only ``register`` and ``password_reset`` purposes are accepted.
    """
    if request.purpose not in _ALLOWED_PURPOSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purpose must be 'register' or 'password_reset'"
        )

    is_valid, two_factor_code = verify_2fa_code(
        db=db,
        email=request.email,
        code=request.code,
        purpose=request.purpose
    )

    if not is_valid or not two_factor_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )

    return Verify2FACodeResponse(
        verified=True,
        message="Code verified successfully"
    )
