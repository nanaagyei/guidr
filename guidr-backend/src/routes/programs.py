"""Program routes."""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from src.db import get_db
from src.models.program import Program
from src.models.institution import Institution
from src.schemas.program import ProgramResponse, ProgramDetailResponse
from src.services.search_service import search_service

router = APIRouter(prefix="/programs", tags=["programs"])


@router.get("", response_model=dict)
async def list_programs(
    degree_level: Optional[str] = Query(None),
    field_of_study: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_tuition: Optional[float] = Query(None),
    max_tuition: Optional[float] = Query(None),
    deadline_before: Optional[date] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    use_search: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List programs with filters and pagination.
    
    Args:
        degree_level: Filter by degree level ('masters' or 'phd')
        field_of_study: Filter by field of study
        country: Filter by institution country
        min_tuition: Minimum tuition filter
        max_tuition: Maximum tuition filter
        deadline_before: Filter programs with deadline before this date
        keyword: Search keyword (searches name and description)
        page: Page number (1-indexed)
        page_size: Number of results per page
        db: Database session
        
    Returns:
        Paginated list of programs
    """
    if use_search and search_service.enabled and (keyword or field_of_study):
        filters = []
        if degree_level:
            filters.append(f"degree_level = '{degree_level}'")
        if country:
            filters.append(f"institution_country = '{country}'")
        result = search_service.search_programs(
            query=keyword or field_of_study or "*",
            filters=" AND ".join(filters) if filters else None,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        if result:
            hits = result.get("hits", [])
            return {
                "results": [
                    {
                        "id": hit["id"],
                        "program_name": hit["name"],
                        "institution_name": hit.get("institution_name"),
                        "city": hit.get("institution_city"),
                        "country": hit.get("institution_country"),
                        "degree_level": hit.get("degree_level"),
                        "field_of_study": hit.get("field_of_study"),
                        "tuition": hit.get("tuition_estimate_per_year"),
                        "deadline": hit.get("application_deadline_primary"),
                    }
                    for hit in hits
                ],
                "page": page,
                "total_pages": result.get("totalPages", 1),
                "total_results": result.get("estimatedTotalHits", len(hits)),
            }

    query = db.query(Program).join(Institution)
    
    if degree_level:
        query = query.filter(Program.degree_level == degree_level)
    
    if field_of_study:
        query = query.filter(Program.field_of_study.ilike(f"%{field_of_study}%"))
    
    if country:
        query = query.filter(Institution.country.ilike(f"%{country}%"))
    
    if min_tuition is not None:
        query = query.filter(Program.tuition_estimate_per_year >= min_tuition)
    
    if max_tuition is not None:
        query = query.filter(Program.tuition_estimate_per_year <= max_tuition)
    
    if deadline_before:
        query = query.filter(
            (Program.application_deadline_primary <= deadline_before) |
            (Program.application_deadline_secondary <= deadline_before)
        )
    
    if keyword:
        query = query.filter(
            (Program.name.ilike(f"%{keyword}%")) |
            (Program.description.ilike(f"%{keyword}%"))
        )
    
    # Get total count
    total_results = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    programs = query.offset(offset).limit(page_size).all()
    
    # Format results
    results = []
    for program in programs:
        results.append({
            "id": str(program.id),
            "program_name": program.name,
            "institution_name": program.institution.name,
            "city": program.institution.city,
            "country": program.institution.country,
            "degree_level": program.degree_level,
            "field_of_study": program.field_of_study,
            "tuition": float(program.tuition_estimate_per_year) if program.tuition_estimate_per_year else None,
            "deadline": program.application_deadline_primary.isoformat() if program.application_deadline_primary else None,
        })
    
    total_pages = (total_results + page_size - 1) // page_size
    
    return {
        "results": results,
        "page": page,
        "total_pages": total_pages,
        "total_results": total_results,
    }


@router.get("/{program_id}", response_model=ProgramDetailResponse)
async def get_program(
    program_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed program information.
    
    Args:
        program_id: Program UUID
        db: Database session
        
    Returns:
        Detailed program information
        
    Raises:
        HTTPException: If program not found
    """
    from uuid import UUID
    
    try:
        program_uuid = UUID(program_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid program ID format"
        )
    
    program = db.query(Program).filter(Program.id == program_uuid).first()
    
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found"
        )
    
    # Compute enrichment metadata
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    staleness_window = timedelta(days=14)
    last_updated = program.last_scraped_at
    is_stale = (now - last_updated > staleness_window) if last_updated else True

    # Format response with institution and tags
    response_data = {
        "id": program.id,
        "institution_id": program.institution_id,
        "name": program.name,
        "degree_level": program.degree_level,
        "delivery_mode": program.delivery_mode,
        "field_of_study": program.field_of_study,
        "research_or_coursework": program.research_or_coursework,
        "description": program.description,
        "application_deadline_primary": program.application_deadline_primary,
        "application_deadline_secondary": program.application_deadline_secondary,
        "tuition_estimate_per_year": program.tuition_estimate_per_year,
        "application_fee": program.application_fee,
        "website_url": program.website_url,
        "program_features": program.program_features,
        "data_completeness_score": program.data_completeness_score or 0,
        "data_source": program.data_source or "unknown",
        "institution": {
            "id": str(program.institution.id),
            "name": program.institution.name,
            "country": program.institution.country,
            "city": program.institution.city,
        },
        "tags": [{"tag_type": tag.tag_type, "value": tag.value} for tag in program.tags],
        "enrichment": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "is_stale": is_stale,
        },
    }

    return response_data

