"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from datetime import datetime, timedelta
from src.db import get_db
from src.models.user import User
from src.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    VerifyCredentialsRequest,
    VerifyCredentialsResponse,
    CheckEmailRequest,
    CheckEmailResponse,
)
from src.utils.password import hash_password, verify_password
from src.utils.jwt import create_access_token
from src.utils.two_factor import verify_2fa_code
from src.dependencies.auth import get_current_user
import logging

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_DB_UNAVAILABLE_MSG = (
    "We\u2019re having trouble connecting to our database. "
    "Please try again in a few minutes."
)


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(
    request: CheckEmailRequest,
    db: Session = Depends(get_db)
):
    """Check if an email is already registered.

    Returns exists=True if there's an account with this email,
    otherwise exists=False.
    """
    try:
        user = db.query(User).filter(User.email == request.email).first()
    except (OperationalError, ProgrammingError) as e:
        logger.error("Database error during check_email", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_DB_UNAVAILABLE_MSG,
        )

    if user:
        return CheckEmailResponse(
            exists=True,
            message="An account already exists with this email. You can log in or reset your password.",
        )

    return CheckEmailResponse(
        exists=False,
        message="No account found with this email. You can create a new account.",
    )


@router.post("/verify-credentials", response_model=VerifyCredentialsResponse)
async def verify_credentials(
    credentials: VerifyCredentialsRequest,
    db: Session = Depends(get_db)
):
    """Verify user credentials (email + password check only).

    This endpoint checks if the email and password are correct.
    Used by the frontend before sending a 2FA code during registration
    or password-reset flows.
    """
    try:
        user = db.query(User).filter(User.email == credentials.email).first()
    except (OperationalError, ProgrammingError) as e:
        logger.error("Database error during verify_credentials", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_DB_UNAVAILABLE_MSG,
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted"
        )

    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    return VerifyCredentialsResponse(
        verified=True,
        message="Credentials verified successfully"
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    response: Response,
    db: Session = Depends(get_db)
):
    """Register a new user (requires email 2FA verification)."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_bytes = len(user_data.password.encode('utf-8'))
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    if password_bytes > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be longer than 72 bytes"
        )

    if not user_data.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is required. Please request a code first."
        )

    is_valid, two_factor_code = verify_2fa_code(
        db=db,
        email=user_data.email,
        code=user_data.verification_code,
        purpose="register"
    )

    if not is_valid or not two_factor_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )

    try:
        hashed_password = hash_password(user_data.password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    two_factor_code.user_id = new_user.id
    db.commit()

    token = create_access_token(str(new_user.id), new_user.email, new_user.role)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=7 * 24 * 60 * 60,
    )

    return UserResponse(
        id=str(new_user.id),
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        created_at=new_user.created_at.isoformat() if new_user.created_at else ""
    )


@router.post("/login", response_model=UserResponse)
async def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login user with email + password (no 2FA code required).

    When ``remember_me`` is True the JWT and cookie both persist for 30 days;
    otherwise the cookie is session-scoped and the token expires in 24 hours.
    """
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted"
        )

    if not user.password_hash or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if user_data.remember_me:
        token_expires = timedelta(days=30)
    else:
        token_expires = timedelta(hours=24)

    token = create_access_token(
        str(user.id), user.email, user.role, expires_delta=token_expires
    )

    cookie_kwargs = dict(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    if user_data.remember_me:
        cookie_kwargs["max_age"] = 30 * 24 * 60 * 60

    response.set_cookie(**cookie_kwargs)

    user.last_login_at = datetime.utcnow()
    db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing session cookie."""
    response.delete_cookie(key="session", samesite="lax")
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        created_at=current_user.created_at.isoformat() if current_user.created_at else ""
    )
