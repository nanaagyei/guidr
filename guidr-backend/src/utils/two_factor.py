"""Utilities for two-factor authentication."""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.two_factor_code import TwoFactorCode
from src.models.user import User


def generate_2fa_code() -> str:
    """Generate a random 6-digit code.
    
    Returns:
        6-digit code as string
    """
    return f"{random.randint(100000, 999999)}"


def create_2fa_code(
    db: Session,
    user_id: str,
    email: str,
    purpose: str,
    expires_in_minutes: int = 10
) -> TwoFactorCode:
    """Create a new 2FA code record.
    
    Args:
        db: Database session
        user_id: User ID (can be None for registration)
        email: Email address to send code to
        purpose: Purpose of the code ('register' or 'login')
        expires_in_minutes: Minutes until code expires
        
    Returns:
        Created TwoFactorCode object
    """
    # Invalidate any existing unused codes for this email and purpose
    existing_codes = db.query(TwoFactorCode).filter(
        TwoFactorCode.email == email,
        TwoFactorCode.purpose == purpose,
        TwoFactorCode.is_used == False,
        TwoFactorCode.expires_at > datetime.utcnow()
    ).all()
    
    for code in existing_codes:
        code.is_used = True
        code.used_at = datetime.utcnow()
    
    # Generate new code
    code = generate_2fa_code()
    expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    
    two_factor_code = TwoFactorCode(
        user_id=user_id if user_id else None,
        code=code,
        email=email,
        purpose=purpose,
        expires_at=expires_at,
    )
    
    db.add(two_factor_code)
    db.commit()
    db.refresh(two_factor_code)
    
    return two_factor_code


def verify_2fa_code(
    db: Session,
    email: str,
    code: str,
    purpose: str
) -> tuple[bool, TwoFactorCode | None]:
    """Verify a 2FA code.
    
    Args:
        db: Database session
        email: Email address
        code: 6-digit code to verify
        purpose: Purpose of the code ('register' or 'login')
        
    Returns:
        Tuple of (is_valid, TwoFactorCode object or None)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # First, check if code exists (even if used or expired) for debugging
    all_codes = db.query(TwoFactorCode).filter(
        TwoFactorCode.email == email,
        TwoFactorCode.code == code,
        TwoFactorCode.purpose == purpose,
    ).all()
    
    if all_codes:
        logger.info(f"Found {len(all_codes)} code(s) matching email={email}, code={code}, purpose={purpose}")
        for c in all_codes:
            logger.info(f"  Code: used={c.is_used}, expires_at={c.expires_at}, now={datetime.utcnow()}")
    
    # Now find valid code
    two_factor_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.email == email,
        TwoFactorCode.code == code,
        TwoFactorCode.purpose == purpose,
        TwoFactorCode.is_used == False,
        TwoFactorCode.expires_at > datetime.utcnow()
    ).first()
    
    if not two_factor_code:
        logger.warning(f"Invalid or expired code: email={email}, code={code}, purpose={purpose}")
        return False, None
    
    # Mark as used
    two_factor_code.is_used = True
    two_factor_code.used_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Successfully verified 2FA code for email={email}, purpose={purpose}")
    return True, two_factor_code

