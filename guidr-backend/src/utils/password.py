"""Password hashing and verification utilities."""
import bcrypt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from src.models.password_history import PasswordHistory

# Create password context with bcrypt
# Use lazy initialization to avoid bug detection issues
_pwd_context = None


def _get_pwd_context():
    """Get or create password context with lazy initialization."""
    global _pwd_context
    if _pwd_context is None:
        _pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
        )
    return _pwd_context


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt.

    Uses bcrypt directly to avoid passlib initialization issues.

    Args:
        plain_password: The plain text password to hash (max 72 bytes)

    Returns:
        Hashed password string

    Raises:
        ValueError: If password is longer than 72 bytes
    """
    # Bcrypt has a 72-byte limit
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")

    # Hash using bcrypt directly
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Fallback to passlib if bcrypt direct check fails
        return _get_pwd_context().verify(plain_password, hashed_password)


def check_password_in_history(db: Session, user_id: str, plain_password: str, current_password_hash: str = None) -> bool:
    """Check if a password was previously used by the user (including current password).

    Args:
        db: Database session
        user_id: User ID
        plain_password: Plain text password to check
        current_password_hash: Optional current password hash to also check against

    Returns:
        True if password was previously used (including current), False otherwise
    """
    # Check against current password if provided
    if current_password_hash and verify_password(plain_password, current_password_hash):
        return True

    # Get all password history for this user
    password_history = db.query(PasswordHistory).filter(
        PasswordHistory.user_id == user_id
    ).all()

    # Check against all previous passwords
    for old_hash in password_history:
        if verify_password(plain_password, old_hash.password_hash):
            return True

    return False


def save_password_to_history(db: Session, user_id: str, password_hash: str) -> None:
    """Save a password hash to the user's password history.

    Args:
        db: Database session
        user_id: User ID
        password_hash: Hashed password to save
    """
    password_history = PasswordHistory(
        user_id=user_id,
        password_hash=password_hash
    )
    db.add(password_history)
    db.commit()

    # Keep only last 5 passwords in history
    from sqlalchemy import desc
    all_history = db.query(PasswordHistory).filter(
        PasswordHistory.user_id == user_id
    ).order_by(desc(PasswordHistory.created_at)).all()

    if len(all_history) > 5:
        for old_record in all_history[5:]:
            db.delete(old_record)
        db.commit()


class PasswordPolicyError(ValueError):
    """A new password failed the strength, length or reuse rules."""


def validate_new_password(db: Session, user_id: str, new_password: str, current_password_hash: str = None) -> None:
    """Apply the rules every new password must pass (reset and change share them).

    Args:
        db: Database session
        user_id: User ID
        new_password: Proposed plain text password
        current_password_hash: The user's current hash, which also counts as "previously used"

    Raises:
        PasswordPolicyError: With a user-facing message if any rule fails.
    """
    from src.utils.password_strength import check_password_strength

    strength_check = check_password_strength(new_password)
    if not strength_check["is_valid"]:
        raise PasswordPolicyError(f"Weak password. {', '.join(strength_check['feedback'])}")

    if len(new_password.encode('utf-8')) > 72:
        raise PasswordPolicyError("Password cannot be longer than 72 bytes")

    if check_password_in_history(db, user_id, new_password, current_password_hash):
        raise PasswordPolicyError(
            "You cannot reuse a previous password. Please choose a different password."
        )
