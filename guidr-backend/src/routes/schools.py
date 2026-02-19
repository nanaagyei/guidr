"""School/Institution routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from src.db import get_db
from src.models.institution import Institution
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

