"""Recommendation routes — AI-powered via dossier pipeline."""
import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from src.db import get_db
from src.models.recommendation_session import RecommendationSession, RecommendationStatus
from src.models.recommendation_result import RecommendationResult
from src.models.saved_recommendation import SavedRecommendation
from src.models.user_profile import UserProfile
from src.models.user import User
from src.models.program import Program
from src.models.institution import Institution
from src.dependencies.auth import get_current_user
from src.dependencies.rate_limit import endpoint_rate_limit
from src.dependencies.feature_gate import require_level

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

# --- Idempotency helpers (Redis-backed, 1-hour TTL) ---
_IDEMPOTENCY_TTL = 3600  # 1 hour


def _idempotency_key_name(user_id: str, key: str) -> str:
    return f"guidr:idem:{user_id}:{key}"


def _check_idempotency(user_id: str, key: str) -> dict | None:
    """Return cached response if the idempotency key was seen recently."""
    import json
    try:
        from src.dependencies.rate_limit import _get_redis
        r = _get_redis()
        raw = r.get(_idempotency_key_name(user_id, key))
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _store_idempotency(user_id: str, key: str, response: dict) -> None:
    """Cache the response under the idempotency key with a TTL."""
    import json
    try:
        from src.dependencies.rate_limit import _get_redis
        r = _get_redis()
        r.setex(
            _idempotency_key_name(user_id, key),
            _IDEMPOTENCY_TTL,
            json.dumps(response, default=str),
        )
    except Exception:
        pass

# Allowlist to prevent injection of arbitrary strings into LLM prompt context
_VALID_TRIGGER_SOURCES = frozenset({
    "manual", "profile_update", "schedule", "onboarding", "dashboard", "dashboard_button", "api"
})


def _sanitize_trigger_source(trigger_source: Optional[str]) -> str:
    """Normalize trigger_source to allowlist; default to 'manual' on mismatch."""
    if trigger_source is None:
        return "manual"
    cleaned = trigger_source.strip()[:50]
    return cleaned if cleaned in _VALID_TRIGGER_SOURCES else "manual"


def _build_result_dict(result: RecommendationResult, db: Session) -> dict:
    """Build a result dict from a RecommendationResult, handling both AI and legacy paths."""
    # Check for saved status
    saved = db.query(SavedRecommendation).filter(
        SavedRecommendation.recommendation_result_id == result.id
    ).first()

    if result.program_id:
        # Legacy path: join to Program/Institution
        program = db.query(Program).filter(Program.id == result.program_id).first()
        if program:
            institution = db.query(Institution).filter(Institution.id == program.institution_id).first()
            return {
                "result_id": str(result.id),
                "program_id": str(result.program_id),
                "program_name": program.name,
                "institution_name": institution.name if institution else result.school_name,
                "institution_city": institution.city if institution else result.institution_city,
                "institution_country": institution.country if institution else result.institution_country,
                "score": float(result.score),
                "tier": result.tier,
                "explanation": result.explanation,
                "reason_features": result.reason_features,
                "rank": result.rank,
                "funding_summary": result.funding_summary,
                "deadline": result.deadline,
                "website_url": result.website_url or program.website_url,
                "is_saved": saved is not None,
                "saved_id": str(saved.id) if saved else None,
            }

    # AI path: metadata stored directly on result
    return {
        "result_id": str(result.id),
        "program_id": None,
        "program_name": result.program_name,
        "institution_name": result.school_name,
        "institution_city": result.institution_city,
        "institution_country": result.institution_country,
        "score": float(result.score),
        "tier": result.tier,
        "explanation": result.explanation,
        "reason_features": result.reason_features,
        "rank": result.rank,
        "funding_summary": result.funding_summary,
        "deadline": result.deadline,
        "website_url": result.website_url,
        "is_saved": saved is not None,
        "saved_id": str(saved.id) if saved else None,
    }


# ──────────────────────────────────────────────
# POST /recommendations/run  (advanced, job-based)
# ──────────────────────────────────────────────

@router.post("/run")
async def run_recommendations(
    trigger_source: Optional[str] = None,
    force_refresh: bool = False,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(require_level(2)),
    db: Session = Depends(get_db),
):
    """Run AI-powered recommendations via the dossier pipeline.

    Async: returns a job_id for polling via GET /pipeline/jobs/{job_id}.
    Returns cached result if fresh (within 7 days).
    Requires profile completion Level 2 (targeting complete).

    Supports Idempotency-Key header: if the same key is reused within 1 hour,
    returns the existing result instead of creating a duplicate job.
    """
    from src.services.dossier_service import DossierService

    # --- Idempotency check ---
    if idempotency_key:
        cached = _check_idempotency(str(current_user.id), idempotency_key)
        if cached is not None:
            return cached

    trigger_source = _sanitize_trigger_source(trigger_source)

    service = DossierService(db)
    result = service.request_recommendations(
        user_id=str(current_user.id),
        trigger_source=trigger_source,
        force=force_refresh,
    )

    resp = {"status": result.status}
    if result.job:
        resp["job_id"] = str(result.job.id)
    if result.cache_entry:
        resp["cache"] = {
            "value_json": result.cache_entry.value_json,
            "confidence": float(result.cache_entry.confidence) if result.cache_entry.confidence else None,
            "computed_at": result.cache_entry.computed_at.isoformat() if result.cache_entry.computed_at else None,
            "citations_json": result.cache_entry.citations_json or [],
        }
    if result.message:
        resp["message"] = result.message

    # Store idempotency result
    if idempotency_key:
        _store_idempotency(str(current_user.id), idempotency_key, resp)

    return resp


# ──────────────────────────────────────────────
# POST /recommendations/request  (frontend default)
# ──────────────────────────────────────────────

@router.post("/request")
async def request_recommendations(
    trigger_source: Optional[str] = None,
    current_user: User = Depends(require_level(2)),
    db: Session = Depends(get_db),
):
    """Request AI-powered recommendations via the dossier pipeline.

    Creates a session upfront (status=pending), dispatches the pipeline
    asynchronously, and returns the session_id for polling via
    GET /recommendations/session/{session_id}.
    """
    from src.services.dossier_service import DossierService

    trigger_source = _sanitize_trigger_source(trigger_source)

    # Load profile for snapshot
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not found. Please complete your profile first.",
        )

    profile_snapshot = {
        "intended_degree": profile.intended_degree,
        "primary_field_of_study": profile.primary_field_of_study,
        "secondary_fields": profile.secondary_fields,
        "preferred_countries": profile.preferred_countries,
        "program_style_preference": profile.program_style_preference,
        "funding_priority": profile.funding_priority,
    }

    # Create session upfront so frontend can poll by session_id
    session = RecommendationSession(
        user_id=current_user.id,
        trigger_source=trigger_source,
        input_profile_snapshot=profile_snapshot,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Dispatch to dossier pipeline (async via Celery, inline fallback)
    try:
        service = DossierService(db)
        result = service.request_recommendations(
            user_id=str(current_user.id),
            trigger_source=trigger_source,
            session_id=str(session.id),
        )

        if result.status == "cache_hit":
            # Cache exists, but does a completed session with results exist?
            latest = db.query(RecommendationSession).filter(
                RecommendationSession.user_id == current_user.id,
                RecommendationSession.status == "completed",
            ).order_by(RecommendationSession.created_at.desc()).first()

            if latest:
                # Check it actually has result rows
                result_count = db.query(RecommendationResult).filter(
                    RecommendationResult.recommendation_session_id == latest.id,
                ).count()
                if result_count > 0:
                    # Remove our pending session and return the existing one
                    db.delete(session)
                    db.commit()
                    return {
                        "session_id": str(latest.id),
                        "status": "completed",
                    }

            # Cache entry exists but no session has actual results.
            # Force a fresh pipeline run, bypassing the stale cache.
            logger.info("Cache hit but no completed session with results; forcing fresh run")
            result = service.request_recommendations(
                user_id=str(current_user.id),
                trigger_source=trigger_source,
                session_id=str(session.id),
                force=True,
            )

        if result.status == "quota_exceeded":
            session.status = "failed"
            session.error_message = result.message or "Daily quota exceeded"
            db.commit()
            return {
                "session_id": str(session.id),
                "status": "failed",
                "error_message": session.error_message,
            }

        # Check if the pipeline ran inline (synchronous fallback when Celery
        # is unavailable). If so, the session is already completed.
        db.refresh(session)
        if session.status in ("completed", "failed"):
            resp = {
                "session_id": str(session.id),
                "status": session.status,
            }
            if session.status == "failed":
                resp["error_message"] = session.error_message or "Pipeline failed"
            return resp

        # Normal case: pipeline job enqueued, frontend polls session status
        return {
            "session_id": str(session.id),
            "status": "pending",
        }

    except Exception as e:
        logger.error("Failed to dispatch recommendation pipeline: %s", e)
        # Rollback any broken transaction before attempting error update
        db.rollback()
        try:
            session.status = "failed"
            session.error_message = str(e)[:500]
            db.commit()
        except Exception:
            db.rollback()
        return {
            "session_id": str(session.id),
            "status": "failed",
            "error_message": str(e)[:500],
        }


# ──────────────────────────────────────────────
# GET /recommendations/latest
# ──────────────────────────────────────────────

@router.get("/latest")
async def get_latest_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the latest completed recommendation session with results."""
    session = db.query(RecommendationSession).filter(
        RecommendationSession.user_id == current_user.id,
        RecommendationSession.status == "completed",
    ).order_by(RecommendationSession.created_at.desc()).first()

    if not session:
        return {
            "session_id": None,
            "created_at": None,
            "completed_at": None,
            "results": [],
        }

    results = db.query(RecommendationResult).filter(
        RecommendationResult.recommendation_session_id == session.id
    ).order_by(RecommendationResult.rank.asc()).all()

    program_results = [_build_result_dict(r, db) for r in results]

    return {
        "session_id": str(session.id),
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "results": program_results,
    }


# ──────────────────────────────────────────────
# GET /recommendations/session/{session_id}
# ──────────────────────────────────────────────

@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific recommendation session by ID."""
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == UUID(session_id),
        RecommendationSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    program_results = []
    if session.status == "completed":
        results = db.query(RecommendationResult).filter(
            RecommendationResult.recommendation_session_id == session.id
        ).order_by(RecommendationResult.rank.asc()).all()
        program_results = [_build_result_dict(r, db) for r in results]

    return {
        "session_id": str(session.id),
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "error_message": session.error_message,
        "results": program_results,
    }


# ──────────────────────────────────────────────
# GET /recommendations/history
# ──────────────────────────────────────────────

@router.get("/history")
async def get_recommendation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all recommendation sessions for the user."""
    sessions = db.query(RecommendationSession).filter(
        RecommendationSession.user_id == current_user.id
    ).order_by(RecommendationSession.created_at.desc()).all()

    session_list = []
    for session in sessions:
        result_count = 0
        if session.status == "completed":
            result_count = db.query(RecommendationResult).filter(
                RecommendationResult.recommendation_session_id == session.id
            ).count()

        session_list.append({
            "session_id": str(session.id),
            "status": session.status,
            "created_at": session.created_at.isoformat(),
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "result_count": result_count,
        })

    return {"sessions": session_list}


# ──────────────────────────────────────────────
# POST /recommendations/results/{result_id}/save
# ──────────────────────────────────────────────

@router.post("/results/{result_id}/save")
async def save_recommendation(
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a recommended school, materializing Institution/Program records
    and triggering deep research pipelines (school dossier, professor matching,
    funding research)."""
    from src.services.dossier_service import DossierService

    # 1. Load result and verify ownership
    result = db.query(RecommendationResult).filter(
        RecommendationResult.id == UUID(result_id),
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation result not found")

    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == result.recommendation_session_id,
        RecommendationSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # 2. Check if already saved
    existing = db.query(SavedRecommendation).filter(
        SavedRecommendation.recommendation_result_id == result.id,
    ).first()
    if existing:
        return {
            "saved_id": str(existing.id),
            "status": existing.research_status,
            "message": "Already saved",
        }

    # 3. Find or create Institution
    institution = None
    school_name = result.school_name or result.program_name or ""
    if school_name:
        # Case-insensitive exact match first
        institution = db.query(Institution).filter(
            Institution.name.ilike(school_name),
            Institution.is_deleted == False,
        ).first()

        if not institution:
            # Try partial match
            institution = db.query(Institution).filter(
                Institution.name.ilike(f"%{school_name}%"),
                Institution.is_deleted == False,
            ).first()

        if not institution:
            # Create new institution from AI data
            institution = Institution(
                name=school_name,
                country=result.institution_country or "United States",
                city=result.institution_city,
                website_url=result.website_url,
                data_source="ai_recommendation",
            )
            db.add(institution)
            db.flush()

    # 4. Find or create Program
    program = None
    if institution and result.program_name:
        program = db.query(Program).filter(
            Program.institution_id == institution.id,
            Program.name.ilike(result.program_name),
        ).first()

        if not program:
            # Load user's intended degree for the program
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == current_user.id
            ).first()

            program = Program(
                institution_id=institution.id,
                name=result.program_name,
                degree_level=profile.intended_degree if profile else "masters",
                field_of_study=profile.primary_field_of_study if profile else None,
                website_url=result.website_url,
                data_source="ai_recommendation",
            )
            db.add(program)
            db.flush()

    # 5. Link result to materialized program
    if program:
        result.program_id = program.id
    db.flush()

    # 6. Create SavedRecommendation
    saved = SavedRecommendation(
        user_id=current_user.id,
        recommendation_result_id=result.id,
        institution_id=institution.id if institution else None,
        program_id=program.id if program else None,
        research_status="running",
    )
    db.add(saved)
    db.flush()

    # 7. Trigger deep research pipelines
    service = DossierService(db)
    job_ids = {}

    if institution:
        # School dossier
        try:
            dossier_result = service.request_school_dossier(
                school_id=str(institution.id),
                user_id=str(current_user.id),
            )
            if dossier_result.job:
                saved.school_dossier_job_id = dossier_result.job.id
                job_ids["school_dossier"] = str(dossier_result.job.id)
        except Exception as e:
            logger.warning("Failed to dispatch school dossier: %s", e)

        # Professor matching
        try:
            profile = db.query(UserProfile).filter(
                UserProfile.user_id == current_user.id
            ).first()
            research_interests = (profile.research_areas or []) if profile else []
            if not research_interests and profile:
                research_interests = [profile.primary_field_of_study] if profile.primary_field_of_study else []

            prof_result = service.request_professor_matches(
                school_id=str(institution.id),
                user_id=str(current_user.id),
                research_interests=research_interests,
            )
            if prof_result.job:
                saved.professor_match_job_id = prof_result.job.id
                job_ids["professor_match"] = str(prof_result.job.id)
        except Exception as e:
            logger.warning("Failed to dispatch professor matching: %s", e)

        # Funding dossier
        try:
            funding_result = service.request_funding_dossier(
                school_id=str(institution.id),
                user_id=str(current_user.id),
                program_id=str(program.id) if program else None,
            )
            if funding_result.job:
                saved.funding_dossier_job_id = funding_result.job.id
                job_ids["funding_dossier"] = str(funding_result.job.id)
        except Exception as e:
            logger.warning("Failed to dispatch funding dossier: %s", e)

    db.commit()

    return {
        "saved_id": str(saved.id),
        "status": saved.research_status,
        "institution_id": str(institution.id) if institution else None,
        "program_id": str(program.id) if program else None,
        "job_ids": job_ids,
    }


# ──────────────────────────────────────────────
# GET /recommendations/saved
# ──────────────────────────────────────────────

@router.get("/saved")
async def get_saved_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all saved recommendations with enrichment status."""
    saved_items = db.query(SavedRecommendation).filter(
        SavedRecommendation.user_id == current_user.id,
    ).order_by(SavedRecommendation.saved_at.desc()).all()

    results = []
    for saved in saved_items:
        result = db.query(RecommendationResult).filter(
            RecommendationResult.id == saved.recommendation_result_id
        ).first()
        if not result:
            continue

        item = {
            "saved_id": str(saved.id),
            "result_id": str(result.id),
            "school_name": result.school_name,
            "program_name": result.program_name,
            "institution_city": result.institution_city,
            "institution_country": result.institution_country,
            "score": float(result.score),
            "tier": result.tier,
            "explanation": result.explanation,
            "funding_summary": result.funding_summary,
            "deadline": result.deadline,
            "website_url": result.website_url,
            "saved_at": saved.saved_at.isoformat(),
            "research_status": saved.research_status,
            "institution_id": str(saved.institution_id) if saved.institution_id else None,
            "program_id": str(saved.program_id) if saved.program_id else None,
        }

        # Check pipeline job statuses
        from src.models.pipeline_job import PipelineJob
        job_statuses = {}
        for job_field, job_name in [
            ("school_dossier_job_id", "school_dossier"),
            ("professor_match_job_id", "professor_match"),
            ("funding_dossier_job_id", "funding_dossier"),
        ]:
            job_id = getattr(saved, job_field)
            if job_id:
                job = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
                job_statuses[job_name] = job.status if job else "unknown"
        item["job_statuses"] = job_statuses

        results.append(item)

    return {"saved": results}


# ──────────────────────────────────────────────
# DELETE /recommendations/saved/{saved_id}
# ──────────────────────────────────────────────

@router.delete("/saved/{saved_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave_recommendation(
    saved_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved recommendation."""
    saved = db.query(SavedRecommendation).filter(
        SavedRecommendation.id == UUID(saved_id),
        SavedRecommendation.user_id == current_user.id,
    ).first()

    if not saved:
        raise HTTPException(status_code=404, detail="Saved recommendation not found")

    db.delete(saved)
    db.commit()
