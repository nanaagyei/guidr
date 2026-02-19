"""Two-factor authentication routes."""
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


@router.post("/send", response_model=Send2FACodeResponse)
async def send_2fa_code(
    request: Send2FACodeRequest,
    db: Session = Depends(get_db)
):
    """Send a 2FA verification code to the user's email.
    
    Args:
        request: Request containing email and purpose
        db: Database session
        
    Returns:
        Response confirming code was sent
        
    Raises:
        HTTPException: If user not found (for login) or email sending fails
    """
    # Validate purpose
    if request.purpose not in ["register", "login", "password_reset"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purpose must be 'register', 'login', or 'password_reset'"
        )
    
    # For login and password_reset, verify user exists
    if request.purpose in ["login", "password_reset"]:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        user_id = str(user.id)
    else:
        # For registration, user doesn't exist yet
        user_id = None
    
    # Check for recent code sends to prevent spam (within last 30 seconds)
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
    
    # Create 2FA code
    two_factor_code = create_2fa_code(
        db=db,
        user_id=user_id,
        email=request.email,
        purpose=request.purpose
    )
    
    # Send email
    email_sent = await send_2fa_code_email(
        to_email=request.email,
        code=two_factor_code.code,
        purpose=request.purpose
    )
    
    if not email_sent:
        # Mark code as used since email failed
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
    
    Args:
        request: Request containing email, code, and purpose
        db: Database session
        
    Returns:
        Response indicating if code is valid
        
    Raises:
        HTTPException: If code is invalid or expired
    """
    # Validate purpose
    if request.purpose not in ["register", "login", "password_reset"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purpose must be 'register', 'login', or 'password_reset'"
        )
    
    # Verify code
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

