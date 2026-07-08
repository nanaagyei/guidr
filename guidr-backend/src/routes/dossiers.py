"""Dossier routes for agentic enrichment."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from src.db import get_db
from src.dependencies.auth import get_current_user
from src.dependencies.rate_limit import endpoint_rate_limit
from src.models.user import User
from src.schemas.dossier_schemas import (
    DossierRequest,
    FundingDossierRequest,
    ProfessorMatchRequest,
)
from src.services.dossier_service import DossierService

router = APIRouter(prefix="/dossiers", tags=["dossiers"])


def _build_response(result) -> dict:
    """Convert DossierResult to API response."""
    resp = {"status": result.status}
    if result.job:
        resp["job_id"] = str(result.job.id)
    if result.cache_entry:
        resp["cache"] = {
            "value_json": result.cache_entry.value_json,
            "confidence": float(result.cache_entry.confidence) if result.cache_entry.confidence else None,
            "computed_at": result.cache_entry.computed_at.isoformat() if result.cache_entry.computed_at else None,
            "expires_at": result.cache_entry.expires_at.isoformat() if result.cache_entry.expires_at else None,
            "citations_json": result.cache_entry.citations_json or [],
            "evidence_map_json": result.cache_entry.evidence_map_json or {},
        }
    if result.message:
        resp["message"] = result.message
    return resp


@router.post("/schools/{school_id}/research")
async def request_school_dossier(
    school_id: UUID,
    body: DossierRequest = DossierRequest(),
    current_user: User = Depends(endpoint_rate_limit("heavy")),
    db: Session = Depends(get_db),
):
    """Request a school dossier (overview, URLs, requirements, deadlines, funding summary).

    Returns cached result if fresh, otherwise enqueues a pipeline job.
    Poll status via GET /pipeline/jobs/{job_id}.
    """
    service = DossierService(db)
    result = service.request_school_dossier(
        school_id=str(school_id),
        user_id=str(current_user.id),
        force=body.force_refresh,
    )
    return _build_response(result)


@router.post("/schools/{school_id}/professors/match")
async def request_professor_match(
    school_id: UUID,
    body: ProfessorMatchRequest = ProfessorMatchRequest(),
    current_user: User = Depends(endpoint_rate_limit("heavy")),
    db: Session = Depends(get_db),
):
    """Request professor matching for a school based on user's research interests.

    Uses OpenAlex + Semantic Scholar APIs to find candidates,
    then Perplexity to rank and synthesize.
    """
    service = DossierService(db)
    result = service.request_professor_matches(
        school_id=str(school_id),
        user_id=str(current_user.id),
        research_interests=body.research_interests,
        department=body.department,
        force=body.force_refresh,
    )
    return _build_response(result)


@router.post("/schools/{school_id}/funding/research")
async def request_funding_dossier(
    school_id: UUID,
    body: FundingDossierRequest = FundingDossierRequest(),
    current_user: User = Depends(endpoint_rate_limit("heavy")),
    db: Session = Depends(get_db),
):
    """Request a funding dossier for a school (fellowships, TA/RA, scholarships, deadlines).

    Optionally scoped to a specific program.
    """
    service = DossierService(db)
    result = service.request_funding_dossier(
        school_id=str(school_id),
        user_id=str(current_user.id),
        program_id=str(body.program_id) if body.program_id else None,
        force=body.force_refresh,
    )
    return _build_response(result)


@router.get("/professors/recommended")
async def get_recommended_professors(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recent professor matches across the user's saved/pinned schools.

    Reads from enrichment_cache entries of kind 'school' with freshness_bucket
    'professor_matches:30d' scoped to the current user.
    """
    import uuid
    from src.models.enrichment_cache import EnrichmentCache

    user_uuid = current_user.id
    now = datetime.utcnow()

    try:
        cache_entries = (
            db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.freshness_bucket == "professor_matches:30d",
                EnrichmentCache.user_id == user_uuid,
                EnrichmentCache.expires_at > now,
            )
            .order_by(EnrichmentCache.computed_at.desc())
            .limit(5)
            .all()
        )

        professors: List[dict] = []
        seen_names: set = set()
        for entry in cache_entries:
            ranked = (entry.value_json or {}).get("ranked_professors", [])
            for prof in ranked:
                name = prof.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    institution_name = prof.get("institution_name") or prof.get("affiliations", [None])[0]
                    professors.append({
                        "id": prof.get("openalex_id") or prof.get("id", ""),
                        "name": name,
                        "full_name": name,
                        "title": prof.get("title"),
                        "institution_name": institution_name,
                        "school_name": institution_name,
                        "research_summary": prof.get("research_summary"),
                        "research_area": prof.get("research_summary"),
                        "interests_tags": prof.get("topics") or prof.get("interests_tags") or [],
                        "tags": prof.get("topics") or prof.get("interests_tags") or [],
                        "is_accepting_students": prof.get("is_likely_accepting") or prof.get("is_accepting_students"),
                        "personal_page_url": prof.get("personal_page_url") or prof.get("profile_url"),
                        "h_index": prof.get("h_index"),
                        "openalex_id": prof.get("openalex_id"),
                        "match_score": prof.get("match_score"),
                    })
                if len(professors) >= limit:
                    break
            if len(professors) >= limit:
                break

        return {"professors": professors[:limit], "total": len(professors)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load professors: {exc}")


@router.get("/deadlines")
async def get_upcoming_deadlines(
    days_ahead: int = 120,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return upcoming application deadlines extracted from dossiers for the user's saved schools.

    Reads school_dossier enrichment_cache entries, extracts deadline fields.
    """
    from src.models.enrichment_cache import EnrichmentCache

    now = datetime.utcnow()
    user_uuid = current_user.id

    try:
        cache_entries = (
            db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.freshness_bucket == "school_dossier:30d",
                EnrichmentCache.user_id == user_uuid,
                EnrichmentCache.expires_at > now,
            )
            .order_by(EnrichmentCache.computed_at.desc())
            .limit(20)
            .all()
        )

        deadlines: List[dict] = []
        for entry in cache_entries:
            dossier = entry.value_json or {}
            school_name = dossier.get("school_name") or dossier.get("name", "Unknown School")
            confidence = float(entry.confidence) if entry.confidence else 0.0

            # Extract deadline from various possible locations in the dossier JSON
            deadline_value = (
                dossier.get("application_deadline")
                or dossier.get("graduate_school", {}).get("general_deadlines")
                or dossier.get("deadline")
            )

            if deadline_value:
                deadlines.append({
                    "school_name": school_name,
                    "entity_id": str(entry.entity_id),
                    "deadline": deadline_value,
                    "confidence": confidence,
                    "is_verified": confidence >= 0.78,
                    "last_updated": entry.computed_at.isoformat() if entry.computed_at else None,
                })

        return {"deadlines": deadlines}

    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to load deadlines: {exc}"
        )
