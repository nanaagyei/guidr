"""Password history model to prevent password reuse."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from src.models.base import Base


class PasswordHistory(Base):
    """Model for storing user password history to prevent reuse."""
    
    __tablename__ = "password_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    password_hash = Column(String, nullable=False)  # Hashed password
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

