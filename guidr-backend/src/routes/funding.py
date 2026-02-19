"""Funding opportunity routes."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, contains_eager, joinedload

from src.db import get_db
from src.dependencies.auth import get_current_user
from src.models.funding_opportunity import FundingOpportunity
from src.models.institution import Institution
from src.models.user import User
from src.services.search_service import search_service

router = APIRouter(prefix="/funding", tags=["funding"])


@router.get("")
async def list_funding(
    institution_id: Optional[str] = Query(None),
    funding_type: Optional[str] = Query(None),
    covers_tuition: Optional[bool] = Query(None),
    covers_stipend: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    use_search: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List funding opportunities with filtering and pagination.

    Query Parameters:
        institution_id: Filter by institution UUID
        funding_type: Filter by type (fellowship, assistantship, scholarship, grant, waiver)
        covers_tuition: Filter by tuition coverage
        covers_stipend: Filter by stipend coverage
        keyword: Search keyword (name/description)
        country: Filter by institution country
        min_amount: Minimum funding amount
        max_amount: Maximum funding amount
        page: Page number (default 1)
        page_size: Results per page (default 20, max 100)
    """
    # Try Meilisearch first
    if use_search and search_service.enabled and keyword:
        filters = []
        if funding_type:
            filters.append(f"funding_type = '{funding_type}'")
        if covers_tuition is not None:
            filters.append(f"covers_tuition = {str(covers_tuition).lower()}")
        if covers_stipend is not None:
            filters.append(f"covers_stipend = {str(covers_stipend).lower()}")
        if country:
            filters.append(f"institution_country = '{country}'")

        result = search_service.search_funding(
            query=keyword,
            filters=" AND ".join(filters) if filters else None,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        if result:
            hits = result.get("hits", [])
            return {
                "results": hits,
                "page": page,
                "total_pages": result.get("totalPages", 1),
                "total_results": result.get("estimatedTotalHits", len(hits)),
            }

    # Fallback to database query
    query = db.query(FundingOpportunity).join(Institution).options(
        contains_eager(FundingOpportunity.institution)
    )

    if institution_id:
        try:
            query = query.filter(
                FundingOpportunity.institution_id == UUID(institution_id)
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid institution_id format",
            )

    if funding_type:
        query = query.filter(FundingOpportunity.funding_type == funding_type)

    if covers_tuition is not None:
        query = query.filter(FundingOpportunity.covers_tuition == covers_tuition)

    if covers_stipend is not None:
        query = query.filter(FundingOpportunity.covers_stipend == covers_stipend)

    if country:
        query = query.filter(Institution.country.ilike(f"%{country}%"))

    if min_amount is not None:
        query = query.filter(FundingOpportunity.amount_max >= min_amount)

    if max_amount is not None:
        query = query.filter(FundingOpportunity.amount_min <= max_amount)

    if keyword:
        kw_pattern = f"%{keyword}%"
        query = query.filter(
            FundingOpportunity.name.ilike(kw_pattern)
            | FundingOpportunity.description.ilike(kw_pattern)
        )

    total_results = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(FundingOpportunity.name)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    results = []
    for f in items:
        inst = f.institution
        results.append(
            {
                "id": str(f.id),
                "name": f.name,
                "funding_type": f.funding_type,
                "amount_min": float(f.amount_min) if f.amount_min else None,
                "amount_max": float(f.amount_max) if f.amount_max else None,
                "amount_period": f.amount_period,
                "deadline": f.deadline.isoformat() if f.deadline else None,
                "covers_tuition": f.covers_tuition,
                "covers_stipend": f.covers_stipend,
                "is_need_based": f.is_need_based,
                "is_merit_based": f.is_merit_based,
                "institution_id": str(inst.id),
                "institution_name": inst.name,
                "institution_country": inst.country,
                "website_url": f.website_url,
            }
        )

    total_pages = (total_results + page_size - 1) // page_size
    return {
        "results": results,
        "page": page,
        "total_pages": total_pages,
        "total_results": total_results,
    }


@router.get("/{funding_id}")
async def get_funding(
    funding_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific funding opportunity."""
    try:
        funding_uuid = UUID(funding_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid funding_id format",
        )

    funding = (
        db.query(FundingOpportunity)
        .options(joinedload(FundingOpportunity.institution))
        .filter(FundingOpportunity.id == funding_uuid)
        .first()
    )
    if not funding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Funding opportunity not found",
        )

    inst = funding.institution

    # Compute enrichment metadata
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    staleness_window = timedelta(days=14)
    last_updated = funding.created_at  # Funding doesn't have last_scraped_at; use created_at
    is_stale = (now - last_updated > staleness_window) if last_updated else True

    return {
        "id": str(funding.id),
        "name": funding.name,
        "funding_type": funding.funding_type,
        "amount_min": float(funding.amount_min) if funding.amount_min else None,
        "amount_max": float(funding.amount_max) if funding.amount_max else None,
        "amount_period": funding.amount_period,
        "deadline": funding.deadline.isoformat() if funding.deadline else None,
        "eligibility_criteria": funding.eligibility_criteria,
        "description": funding.description,
        "website_url": funding.website_url,
        "is_need_based": funding.is_need_based,
        "is_merit_based": funding.is_merit_based,
        "covers_tuition": funding.covers_tuition,
        "covers_stipend": funding.covers_stipend,
        "source_url": funding.source_url,
        "data_source": funding.data_source,
        "institution": {
            "id": str(inst.id),
            "name": inst.name,
            "country": inst.country,
            "city": inst.city,
        },
        "created_at": funding.created_at.isoformat(),
        "enrichment": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "is_stale": is_stale,
        },
    }


@router.get("/institution/{institution_id}")
async def list_funding_for_institution(
    institution_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all funding opportunities for a specific institution."""
    try:
        inst_uuid = UUID(institution_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid institution_id format",
        )

    institution = db.query(Institution).filter(Institution.id == inst_uuid).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institution not found",
        )

    items = (
        db.query(FundingOpportunity)
        .filter(FundingOpportunity.institution_id == inst_uuid)
        .order_by(FundingOpportunity.funding_type, FundingOpportunity.name)
        .all()
    )

    return {
        "institution": {
            "id": str(institution.id),
            "name": institution.name,
        },
        "funding_opportunities": [
            {
                "id": str(f.id),
                "name": f.name,
                "funding_type": f.funding_type,
                "amount_min": float(f.amount_min) if f.amount_min else None,
                "amount_max": float(f.amount_max) if f.amount_max else None,
                "amount_period": f.amount_period,
                "deadline": f.deadline.isoformat() if f.deadline else None,
                "covers_tuition": f.covers_tuition,
                "covers_stipend": f.covers_stipend,
                "website_url": f.website_url,
            }
            for f in items
        ],
        "total": len(items),
    }
