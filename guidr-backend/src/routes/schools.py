"""School/Institution routes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from src.db import get_db
from src.dependencies.auth import get_current_user
from src.models.institution import Institution
from src.models.user import User
from src.schemas.institution import InstitutionResponse
from src.services.search_service import search_service

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("", response_model=List[InstitutionResponse])
async def list_schools(
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    use_search: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List institutions with optional filters.

    Args:
        country: Filter by country
        city: Filter by city
        name: Search by name (keyword)
        db: Database session

    Returns:
        List of institutions
    """
    if use_search and search_service.enabled and (name or country or city):
        filters = []
        if country:
            filters.append(f"country = '{country}'")
        if city:
            filters.append(f"city = '{city}'")
        search_result = search_service.search_institutions(
            query=name or "*",
            filters=" AND ".join(filters) if filters else None,
            limit=100,
        )
        if search_result:
            return search_result.get("hits", [])

    query = db.query(Institution)

    if country:
        query = query.filter(Institution.country.ilike(f"%{country}%"))

    if city:
        query = query.filter(Institution.city.ilike(f"%{city}%"))

    if name:
        query = query.filter(Institution.name.ilike(f"%{name}%"))

    institutions = query.all()
    return institutions


@router.get("/saved")
async def get_saved_schools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return schools the user has interacted with — either via dossier research
    or from their latest recommendation session.

    Combines:
    1. Schools that have a per-user enrichment_cache dossier entry (actively researched).
    2. Top schools from the user's latest recommendation session.
    """
    from src.models.enrichment_cache import EnrichmentCache
    from src.models.recommendation_session import RecommendationSession
    from src.models.recommendation_result import RecommendationResult
    from src.models.program import Program

    user_uuid = current_user.id
    now = datetime.utcnow()
    results: List[dict] = []
    seen_ids: set = set()

    # 1. Schools with active dossier cache entries (user-scoped)
    try:
        dossier_entries = (
            db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.entity_kind == "school",
                EnrichmentCache.user_id == user_uuid,
                EnrichmentCache.freshness_bucket == "school_dossier:30d",
                EnrichmentCache.expires_at > now,
            )
            .order_by(EnrichmentCache.computed_at.desc())
            .limit(20)
            .all()
        )
        for entry in dossier_entries:
            entity_id_str = str(entry.entity_id)
            if entity_id_str in seen_ids:
                continue
            seen_ids.add(entity_id_str)

            school = db.query(Institution).filter(Institution.id == entry.entity_id).first()
            if school:
                dossier = entry.value_json or {}
                results.append({
                    "id": str(school.id),
                    "name": school.name,
                    "city": school.city,
                    "state_or_province": school.state_or_province,
                    "country": school.country,
                    "website_url": school.website_url,
                    "institution_type": school.institution_type,
                    "public_private": school.public_private,
                    "program_count": dossier.get("program_count"),
                    "in_state_tuition": float(school.in_state_tuition) if school.in_state_tuition else None,
                    "out_of_state_tuition": float(school.out_of_state_tuition) if school.out_of_state_tuition else None,
                    "graduation_rate": float(school.graduation_rate) if school.graduation_rate else None,
                    "data_completeness_score": school.data_completeness_score,
                    "last_enriched_at": entry.computed_at.isoformat() if entry.computed_at else None,
                    "confidence": float(entry.confidence) if entry.confidence else None,
                    "source": "dossier",
                })
    except Exception as exc:
        pass  # Non-fatal — continue with recommendations

    # 2. Schools from latest recommendation session
    try:
        latest_session = (
            db.query(RecommendationSession)
            .filter(
                RecommendationSession.user_id == user_uuid,
                RecommendationSession.status == "completed",
            )
            .order_by(RecommendationSession.created_at.desc())
            .first()
        )
        if latest_session:
            rec_results = (
                db.query(RecommendationResult)
                .filter(RecommendationResult.recommendation_session_id == latest_session.id)
                .order_by(RecommendationResult.rank.asc())
                .limit(15)
                .all()
            )
            for rec in rec_results:
                program = db.query(Program).filter(Program.id == rec.program_id).first()
                if not program:
                    continue
                school = db.query(Institution).filter(Institution.id == program.institution_id).first()
                if not school:
                    continue
                entity_id_str = str(school.id)
                if entity_id_str in seen_ids:
                    continue
                seen_ids.add(entity_id_str)
                results.append({
                    "id": str(school.id),
                    "name": school.name,
                    "city": school.city,
                    "state_or_province": school.state_or_province,
                    "country": school.country,
                    "website_url": school.website_url,
                    "institution_type": school.institution_type,
                    "public_private": school.public_private,
                    "program_count": None,
                    "in_state_tuition": float(school.in_state_tuition) if school.in_state_tuition else None,
                    "out_of_state_tuition": float(school.out_of_state_tuition) if school.out_of_state_tuition else None,
                    "graduation_rate": float(school.graduation_rate) if school.graduation_rate else None,
                    "data_completeness_score": school.data_completeness_score,
                    "last_enriched_at": school.last_enriched_at.isoformat() if school.last_enriched_at else None,
                    "confidence": None,
                    "recommendation_tier": rec.tier,
                    "recommendation_score": float(rec.score) if rec.score else None,
                    "source": "recommendation",
                })
    except Exception:
        pass

    return {"schools": results, "total": len(results)}


@router.get("/{school_id}")
async def get_school(
    school_id: str,
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific institution."""
    try:
        school_uuid = UUID(school_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid school ID format",
        )

    school = db.query(Institution).filter(Institution.id == school_uuid).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found",
        )

    from datetime import datetime, timedelta
    now = datetime.utcnow()
    staleness_window = timedelta(days=30)
    last_updated = school.last_scraped_at
    is_stale = (now - last_updated > staleness_window) if last_updated else True

    return {
        "id": str(school.id),
        "name": school.name,
        "short_name": school.short_name,
        "country": school.country,
        "state_or_province": school.state_or_province,
        "city": school.city,
        "website_url": school.website_url,
        "institution_type": school.institution_type,
        "public_private": school.public_private,
        "description": school.description,
        "acceptance_rate": float(school.acceptance_rate) if school.acceptance_rate else None,
        "enrollment_total": school.enrollment_total,
        "grad_enrollment": school.grad_enrollment,
        "campus_setting": school.campus_setting,
        "academic_calendar": school.academic_calendar,
        "average_cost": float(school.average_cost) if school.average_cost else None,
        "in_state_tuition": float(school.in_state_tuition) if school.in_state_tuition else None,
        "out_of_state_tuition": float(school.out_of_state_tuition) if school.out_of_state_tuition else None,
        "graduation_rate": float(school.graduation_rate) if school.graduation_rate else None,
        "data_completeness_score": school.data_completeness_score,
        "enrichment": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "is_stale": is_stale,
        },
    }
