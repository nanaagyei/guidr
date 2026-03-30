"""RawArtifact model for stored HTML/PDF content metadata."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class RawArtifact(Base):
    """Maps to raw_artifacts table (migration 014).

    Stores metadata about fetched content stored in object storage (MinIO/S3).
    Content itself lives at storage_uri; this row tracks provenance.
    """

    __tablename__ = "raw_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    fetched_from_url = Column(Text, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    artifact_type = Column(String, nullable=False, default="html")  # html, pdf, json, text, image, other
    content_sha256 = Column(String, nullable=False, unique=True)
    byte_size = Column(Integer, nullable=True)
    storage_uri = Column(Text, nullable=False)

    content_type = Column(String, nullable=True)
    http_status = Column(Integer, nullable=True)
    etag = Column(String, nullable=True)
    last_modified = Column(String, nullable=True)

    request_headers = Column(JSON, nullable=False, default=dict)
    response_headers = Column(JSON, nullable=False, default=dict)

    is_parsed = Column(Boolean, nullable=False, default=False)
    parse_notes = Column(Text, nullable=True)

    # Relationships
    source_document = relationship("SourceDocument", back_populates="raw_artifacts")
    extraction_runs = relationship("ExtractionRun", back_populates="raw_artifact")
