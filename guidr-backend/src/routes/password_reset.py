"""Password reset routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from src.db import get_db
from src.models.user import User
from src.schemas.password_reset import (
    RequestPasswordResetRequest,
    RequestPasswordResetResponse,
    VerifyPasswordResetRequest,
    VerifyPasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from src.utils.two_factor import create_2fa_code, verify_2fa_code
from src.utils.password import hash_password, verify_password, check_password_in_history, save_password_to_history
from src.utils.password_strength import check_password_strength
from src.services.email import send_2fa_code_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/password-reset", tags=["password-reset"])

# Store reset tokens temporarily (in production, use Redis)
reset_tokens = {}


@router.post("/request", response_model=RequestPasswordResetResponse)
async def request_password_reset(
    request: RequestPasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset by sending a 2FA code.
    
    Args:
        request: Request containing email
        db: Database session
        
    Returns:
        Response confirming code was sent or indicating account doesn't exist
        
    Raises:
        HTTPException: If email sending fails
    """
    # Verify user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Return a message indicating no account found, but suggest registration
        return RequestPasswordResetResponse(
            message="No account found with this email address. Please check your email or register for a new account.",
            expires_in_minutes=0
        )
    
    # Check for recent code sends (rate limiting)
    from src.models.two_factor_code import TwoFactorCode
    recent_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.email == request.email,
        TwoFactorCode.purpose == "password_reset",
        TwoFactorCode.created_at > datetime.utcnow() - timedelta(seconds=30)
    ).first()
    
    if recent_code:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting another code. A code was recently sent."
        )
    
    # Create 2FA code with purpose "password_reset"
    two_factor_code = create_2fa_code(
        db=db,
        user_id=str(user.id),
        email=request.email,
        purpose="password_reset"
    )
    
    # Send email
    email_sent = await send_2fa_code_email(
        to_email=request.email,
        code=two_factor_code.code,
        purpose="password_reset"
    )
    
    if not email_sent:
        # Mark code as used since email failed
        two_factor_code.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )
    
    return RequestPasswordResetResponse(
        message="A verification code has been sent to your email address.",
        expires_in_minutes=10
    )


@router.post("/verify", response_model=VerifyPasswordResetResponse)
async def verify_password_reset_code(
    request: VerifyPasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Verify the password reset code and generate a reset token.
    
    Args:
        request: Request containing email and code
        db: Database session
        
    Returns:
        Response with reset token
        
    Raises:
        HTTPException: If code is invalid or expired
    """
    # Verify code
    is_valid, two_factor_code = verify_2fa_code(
        db=db,
        email=request.email,
        code=request.code,
        purpose="password_reset"
    )
    
    if not is_valid or not two_factor_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Store token (expires in 15 minutes)
    reset_tokens[reset_token] = {
        "email": request.email,
        "expires_at": datetime.utcnow() + timedelta(minutes=15)
    }
    
    return VerifyPasswordResetResponse(
        verified=True,
        message="Code verified successfully",
        reset_token=reset_token
    )


@router.post("/reset", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset the user's password.
    
    Args:
        request: Request containing email, reset token, and new password
        db: Database session
        
    Returns:
        Response confirming password was reset
        
    Raises:
        HTTPException: If token is invalid, password is weak, or password was previously used
    """
    # Verify reset token
    token_data = reset_tokens.get(request.reset_token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if token_data["email"] != request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match reset token"
        )
    
    if token_data["expires_at"] < datetime.utcnow():
        del reset_tokens[request.reset_token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check password strength
    strength_check = check_password_strength(request.new_password)
    if not strength_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weak password. {', '.join(strength_check['feedback'])}"
        )
    
    # Check password length (bcrypt limit)
    password_bytes = len(request.new_password.encode('utf-8'))
    if password_bytes > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 bytes"
        )
    
    # Check if password was previously used (including current password)
    if check_password_in_history(db, str(user.id), request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot reuse a previous password. Please choose a different password."
        )
    
    # Hash new password
    try:
        new_password_hash = hash_password(request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Save old password to history
    if user.password_hash:
        save_password_to_history(db, str(user.id), user.password_hash)
    
    # Update user password
    user.password_hash = new_password_hash
    db.commit()
    
    # Remove used token
    del reset_tokens[request.reset_token]
    
    logger.info(f"Password reset successful for user {user.email}")
    
    return ResetPasswordResponse(
        message="Password has been reset successfully"
    )

