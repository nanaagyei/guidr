"""JWT token creation and validation utilities."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from src.config import settings


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: User's UUID as string
        email: User's email
        role: User's role (user/admin)
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(days=7)  # 7 day expiration for MVP
    to_encode = {
        "sub": str(user_id),  # Subject (user ID)
        "email": email,
        "role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

