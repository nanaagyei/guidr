"""Professor-Program association (many-to-many)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class ProfessorProgram(Base):
    """Links professors to programs they are associated with."""

    __tablename__ = "professor_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    professor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("professors.id"),
        nullable=False,
        index=True,
    )
    program_id = Column(
        UUID(as_uuid=True),
        ForeignKey("programs.id"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    professor = relationship("Professor", backref="program_associations")
    program = relationship("Program", backref="professor_associations")
