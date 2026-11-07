"""Account self-service: data export, password change and account deletion."""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.models.academic_record import AcademicRecord
from src.models.document import Document
from src.models.document_processing_log import DocumentProcessingLog
from src.models.enrichment_cache import EnrichmentCache
from src.models.essay import Essay
from src.models.essay_review import EssayReview
from src.models.essay_version import EssayVersion
from src.models.outreach_email import OutreachEmail
from src.models.password_history import PasswordHistory
from src.models.recommendation_result import RecommendationResult
from src.models.recommendation_session import RecommendationSession
from src.models.saved_recommendation import SavedRecommendation
from src.models.two_factor_code import TwoFactorCode
from src.models.user import User
from src.models.user_profile import UserProfile
from src.utils.password import (
    hash_password,
    save_password_to_history,
    validate_new_password,
    verify_password,
)

logger = logging.getLogger(__name__)

# Every model holding rows owned by a user, in the order they are deleted (children first).
# tests/routes/test_account_routes.py asserts that every mapped model with a `user_id`
# column appears here, so a new user-owned table cannot be forgotten.
USER_OWNED_MODELS: list[type] = [
    EssayReview,
    EssayVersion,
    Essay,
    DocumentProcessingLog,
    Document,
    AcademicRecord,
    SavedRecommendation,
    RecommendationResult,
    RecommendationSession,
    OutreachEmail,
    EnrichmentCache,
    TwoFactorCode,
    PasswordHistory,
    UserProfile,
]


class InvalidPasswordError(ValueError):
    """The password given for re-authentication is wrong."""


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    return value


def _row(obj: Any, exclude: tuple[str, ...] = ()) -> dict:
    """Serialize a model row's columns, skipping ``exclude``."""
    return {
        col.name: _json_value(getattr(obj, col.key))
        for col in obj.__table__.columns
        if col.name not in exclude
    }


def build_export(db: Session, user: User) -> dict:
    """Assemble everything stored about ``user``.

    Never includes the password hash, password history or two-factor codes.
    """
    uid = user.id
    profile = db.query(UserProfile).filter(UserProfile.user_id == uid).first()

    essays = []
    for essay in db.query(Essay).filter(Essay.user_id == uid).all():
        item = _row(essay)
        item["versions"] = [
            _row(v) for v in db.query(EssayVersion).filter(EssayVersion.essay_id == essay.id).all()
        ]
        item["reviews"] = [
            _row(r) for r in db.query(EssayReview).filter(EssayReview.essay_id == essay.id).all()
        ]
        essays.append(item)

    sessions = []
    for session in db.query(RecommendationSession).filter(RecommendationSession.user_id == uid).all():
        item = _row(session)
        item["results"] = [
            _row(r)
            for r in db.query(RecommendationResult)
            .filter(RecommendationResult.recommendation_session_id == session.id)
            .all()
        ]
        sessions.append(item)

    documents = [
        {
            "filename": d.original_filename,
            "type": d.document_type,
            "status": d.processing_status,
            "uploaded_at": _json_value(d.uploaded_at),
        }
        for d in db.query(Document).filter(Document.user_id == uid).all()
    ]

    research_cache_entries = [
        {
            "entity_kind": c.entity_kind,
            "entity_id": _json_value(c.entity_id),
            "computed_at": _json_value(c.computed_at),
            "value": c.value_json,
        }
        for c in db.query(EnrichmentCache).filter(EnrichmentCache.user_id == uid).all()
    ]

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "created_at": _json_value(user.created_at),
        },
        "profile": _row(profile) if profile else None,
        "academic_records": [
            _row(r) for r in db.query(AcademicRecord).filter(AcademicRecord.user_id == uid).all()
        ],
        "essays": essays,
        "documents": documents,
        "recommendation_sessions": sessions,
        "saved_recommendations": [
            _row(s)
            for s in db.query(SavedRecommendation).filter(SavedRecommendation.user_id == uid).all()
        ],
        "outreach_emails": [
            _row(e) for e in db.query(OutreachEmail).filter(OutreachEmail.user_id == uid).all()
        ],
        "research_cache_entries": research_cache_entries,
    }


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """Change ``user``'s password after re-authenticating them.

    Raises:
        InvalidPasswordError: ``current_password`` is wrong.
        PasswordPolicyError: ``new_password`` fails the reset rules.
    """
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise InvalidPasswordError("Current password is incorrect")

    validate_new_password(db, str(user.id), new_password, user.password_hash)
    new_hash = hash_password(new_password)
    save_password_to_history(db, str(user.id), user.password_hash)
    user.password_hash = new_hash
    db.commit()


def delete_account(db: Session, user: User, password: str, storage: Optional[Any] = None) -> None:
    """Delete everything owned by ``user`` and anonymise the user row.

    Stored files are removed first; a storage failure is logged and does not stop
    the deletion. All row changes happen in one transaction.

    Raises:
        InvalidPasswordError: ``password`` is wrong. Nothing is deleted.
    """
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise InvalidPasswordError("Password is incorrect")

    uid = user.id
    if storage is None:
        from src.services.storage import storage_service as storage

    documents = db.query(Document).filter(Document.user_id == uid).all()
    for doc in documents:
        try:
            if not storage.delete_file(doc.storage_key):
                logger.warning("Stored file for document %s was not deleted", doc.id)
        except Exception:
            logger.exception("Failed to delete stored file for document %s", doc.id)

    essay_ids = db.query(Essay.id).filter(Essay.user_id == uid)
    document_ids = db.query(Document.id).filter(Document.user_id == uid)
    session_ids = db.query(RecommendationSession.id).filter(RecommendationSession.user_id == uid)

    try:
        db.query(EssayReview).filter(EssayReview.essay_id.in_(essay_ids)).delete(
            synchronize_session=False
        )
        db.query(EssayVersion).filter(EssayVersion.essay_id.in_(essay_ids)).delete(
            synchronize_session=False
        )
        db.query(Essay).filter(Essay.user_id == uid).delete(synchronize_session=False)
        db.query(DocumentProcessingLog).filter(
            DocumentProcessingLog.document_id.in_(document_ids)
        ).delete(synchronize_session=False)
        db.query(Document).filter(Document.user_id == uid).delete(synchronize_session=False)
        db.query(AcademicRecord).filter(AcademicRecord.user_id == uid).delete(
            synchronize_session=False
        )
        db.query(SavedRecommendation).filter(SavedRecommendation.user_id == uid).delete(
            synchronize_session=False
        )
        db.query(RecommendationResult).filter(
            RecommendationResult.recommendation_session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        db.query(RecommendationSession).filter(RecommendationSession.user_id == uid).delete(
            synchronize_session=False
        )
        db.query(OutreachEmail).filter(OutreachEmail.user_id == uid).delete(
            synchronize_session=False
        )
        db.query(EnrichmentCache).filter(EnrichmentCache.user_id == uid).delete(
            synchronize_session=False
        )
        # Registration codes are stored before the user exists, keyed by email only.
        db.query(TwoFactorCode).filter(
            (TwoFactorCode.user_id == uid) | (TwoFactorCode.email == user.email)
        ).delete(synchronize_session=False)
        db.query(PasswordHistory).filter(PasswordHistory.user_id == uid).delete(
            synchronize_session=False
        )
        db.query(UserProfile).filter(UserProfile.user_id == uid).delete(synchronize_session=False)

        # Anonymise rather than delete: shared tables may still reference the user id.
        user.email = f"deleted-{uuid.uuid4()}@deleted.invalid"
        user.full_name = None
        user.password_hash = None
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise
