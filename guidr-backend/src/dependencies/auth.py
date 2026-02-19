"""Authentication dependencies for FastAPI routes."""
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.orm import Session
from src.db import get_db
from src.models.user import User
from src.utils.jwt import decode_access_token


async def get_current_user(
    session: str = Cookie(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current authenticated user.
    
    Args:
        session: JWT token from cookie
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is missing or invalid, or user not found
    """
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
