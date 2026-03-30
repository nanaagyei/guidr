"""Authentication dependencies for FastAPI routes."""
from fastapi import Depends, HTTPException, Header, status, Cookie
from sqlalchemy.orm import Session
from typing import Optional
from src.db import get_db
from src.models.user import User
from src.utils.jwt import decode_access_token
from src.config import settings


async def get_current_user(
    session: str = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user from JWT cookie."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_access_token(session)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    from uuid import UUID
    user = db.query(User).filter(User.id == UUID(user_id), User.is_deleted == False).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def require_admin_user(user: User = Depends(get_current_user)) -> User:
    """Ensure the requester has admin privileges."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def require_internal_api_key(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
) -> str:
    """Validate the internal API key for service-to-service calls.

    Expects the header ``X-Internal-Key`` to match
    ``settings.internal_api_key``.  If no key is configured on the
    server the dependency always rejects requests with 503.
    """
    configured_key = settings.internal_api_key
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured on the server",
        )

    if not x_internal_key or x_internal_key != configured_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal API key",
        )

    return x_internal_key


async def require_admin_or_internal_key(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
    session: str = Cookie(None),
    db: Session = Depends(get_db),
) -> str:
    """Accept either a valid admin user session OR an internal API key.

    This allows admin endpoints to be called by both human admins (via
    browser cookie) and by internal services / scripts (via API key
    header), without requiring both.
    """
    # Try internal API key first (cheaper check)
    configured_key = settings.internal_api_key
    if configured_key and x_internal_key and x_internal_key == configured_key:
        return "internal"

    # Fall back to admin user session
    if session:
        payload = decode_access_token(session)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                from uuid import UUID
                user = db.query(User).filter(
                    User.id == UUID(user_id), User.is_deleted == False
                ).first()
                if user and user.role == "admin":
                    return "admin"

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges or valid internal API key required",
    )
