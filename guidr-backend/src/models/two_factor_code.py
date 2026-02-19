"""Two-factor authentication code model."""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timedelta
from src.models.base import Base


class TwoFactorCode(Base):
    """Model for storing 2FA verification codes."""
    
    __tablename__ = "two_factor_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # Nullable for registration
    code = Column(String(6), nullable=False)  # 6-digit code
    email = Column(String, nullable=False)  # Email the code was sent to
    purpose = Column(String, nullable=False)  # 'register' or 'login'
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

