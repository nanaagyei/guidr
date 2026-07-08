"""Professor routes."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from uuid import UUID
from src.db import get_db
from src.models.professor import Professor
from src.models.professor_research_tag import ProfessorResearchTag
from src.models.institution import Institution
from src.models.enrichment_cache import EnrichmentCache
from src.models.funding_opportunity import FundingOpportunity
from src.models.user import User
from src.models.user_profile import UserProfile
from src.models.academic_record import AcademicRecord
from src.models.program import Program
from src.models.outreach_email import OutreachEmail
from src.dependencies.auth import get_current_user
from src.dependencies.feature_gate import require_level
from src.services.email_generator import generate_cold_email, generate_email_template_simple

router = APIRouter(prefix="/professors", tags=["professors"])


@router.get("")
async def list_professors(
    institution_id: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    research_keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List professors with optional filters.
    
    Query Parameters:
        institution_id: Filter by institution
        country: Filter by country (via institution)
        research_keyword: Search in tags and research summary
        page: Page number (default: 1)
        page_size: Results per page (default: 20, max: 100)
    """
    query = db.query(Professor).join(Institution)
    
    # Filter by institution
    if institution_id:
        try:
            query = query.filter(Professor.institution_id == UUID(institution_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid institution_id format"
            )
    
    # Filter by country
    if country:
        query = query.filter(Institution.country.ilike(f'%{country}%'))
    
    # Filter by research keyword
    if research_keyword:
        keyword_pattern = f'%{research_keyword}%'
        # Search in research summary
        summary_match = Professor.research_summary.ilike(keyword_pattern)
        
        # Search in interests_tags (JSON array)
        tags_match = Professor.interests_tags.astext.ilike(keyword_pattern)
        
        # Search in normalized research tags
        tag_join = db.query(ProfessorResearchTag).filter(
            ProfessorResearchTag.tag.ilike(keyword_pattern)
        ).subquery()
        tag_match = Professor.id.in_(
            db.query(tag_join.c.professor_id)
        )
        
        query = query.filter(or_(summary_match, tags_match, tag_match))
    
    # Get total count
    total_count = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    professors = query.order_by(Institution.name, Professor.full_name).offset(offset).limit(page_size).all()
    
    # Build response
    results = []
    for prof in professors:
        institution = prof.institution
        
        # Get research tags
        tags = []
        if prof.interests_tags and isinstance(prof.interests_tags, list):
            tags = prof.interests_tags
        else:
            # Fallback to normalized tags
            research_tags = db.query(ProfessorResearchTag).filter(
                ProfessorResearchTag.professor_id == prof.id
            ).all()
            tags = [tag.tag for tag in research_tags]
        
        results.append({
            "id": str(prof.id),
            "full_name": prof.full_name,
            "title": prof.title,
            "institution_name": institution.name if institution else None,
            "institution_id": str(institution.id) if institution else None,
            "country": institution.country if institution else None,
            "city": institution.city if institution else None,
            "research_summary": prof.research_summary,
            "tags": tags,
            "email": prof.email,
            "personal_page_url": prof.personal_page_url,
            "scholar_profile_url": prof.scholar_profile_url,
        })
    
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        "results": results,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_results": total_count
    }


@router.get("/{professor_id}")
async def get_professor(
    professor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific professor."""
    try:
        professor = db.query(Professor).filter(Professor.id == UUID(professor_id)).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid professor_id format"
        )
    
    if not professor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professor not found"
        )
    
    institution = professor.institution
    
    # Get research tags
    tags = []
    if professor.interests_tags and isinstance(professor.interests_tags, list):
        tags = professor.interests_tags
    else:
        research_tags = db.query(ProfessorResearchTag).filter(
            ProfessorResearchTag.professor_id == professor.id
        ).all()
        tags = [tag.tag for tag in research_tags]
    
    # Compute enrichment metadata
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    staleness_window = timedelta(days=30)
    last_updated = professor.last_scraped_at
    is_stale = (now - last_updated > staleness_window) if last_updated else True

    return {
        "id": str(professor.id),
        "full_name": professor.full_name,
        "title": professor.title,
        "institution": {
            "id": str(institution.id) if institution else None,
            "name": institution.name if institution else None,
            "country": institution.country if institution else None,
            "city": institution.city if institution else None,
        },
        "email": professor.email,
        "personal_page_url": professor.personal_page_url,
        "scholar_profile_url": professor.scholar_profile_url,
        "research_summary": professor.research_summary,
        "tags": tags,
        "is_accepting_students": professor.is_accepting_students,
        "enrichment": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "is_stale": is_stale,
        },
    }


def _compute_topic_overlap(user_interests: list, prof_tags: list) -> dict:
    """Compute topic overlap between user research interests and professor tags."""
    if not user_interests or not prof_tags:
        return {"score": 0, "explanation": "Insufficient data for topic comparison"}

    user_set = {t.lower().strip() for t in user_interests if t}
    prof_set = {t.lower().strip() for t in prof_tags if t}

    if not user_set or not prof_set:
        return {"score": 0, "explanation": "No research interests to compare"}

    intersection = user_set & prof_set
    union = user_set | prof_set
    ratio = len(intersection) / len(union) if union else 0

    # Also check partial keyword overlap for broader matching
    partial_matches = 0
    for u in user_set:
        for p in prof_set:
            if u in p or p in u:
                partial_matches += 1
    partial_ratio = min(partial_matches / max(len(user_set), 1), 1.0)

    score = round(max(ratio, partial_ratio * 0.7) * 100)
    matched = len(intersection)
    total = len(user_set)
    return {
        "score": min(score, 100),
        "explanation": f"{matched} of {total} research areas match" if matched else f"Partial overlap in {partial_matches} areas",
    }


def _compute_activity_score(h_index: int | None, enrichment_data: dict | None) -> dict:
    """Score research activity from h-index and enrichment data."""
    if h_index is not None and h_index > 0:
        score = round(min(h_index / 50, 1.0) * 100)
        papers = enrichment_data.get("paper_count", "N/A") if enrichment_data else "N/A"
        return {"score": score, "explanation": f"h-index {h_index}, {papers} publications"}

    if enrichment_data:
        works = enrichment_data.get("works_count", 0)
        if works:
            score = round(min(works / 100, 1.0) * 100)
            return {"score": score, "explanation": f"{works} published works"}

    return {"score": 0, "explanation": "No publication data available"}


def _compute_availability_score(is_accepting: bool | None) -> dict:
    """Score availability based on accepting students flag."""
    if is_accepting is True:
        return {"score": 100, "explanation": "Accepting students"}
    if is_accepting is False:
        return {"score": 0, "explanation": "Not currently accepting students"}
    return {"score": 50, "explanation": "Availability unknown"}


def _compute_funding_score(funding_count: int) -> dict:
    """Score funding availability at the professor's institution."""
    if funding_count == 0:
        return {"score": 0, "explanation": "No funding opportunities found at institution"}
    score = round(min(funding_count / 5, 1.0) * 100)
    return {"score": score, "explanation": f"{funding_count} funding opportunit{'y' if funding_count == 1 else 'ies'} at institution"}


def _compute_methods_score(user_field: str | None, research_summary: str | None) -> dict:
    """Score methods alignment via keyword overlap in research summary."""
    if not user_field or not research_summary:
        return {"score": 0, "explanation": "Insufficient data for methods comparison"}

    field_keywords = {w.lower() for w in user_field.split() if len(w) > 3}
    summary_lower = research_summary.lower()

    matches = sum(1 for kw in field_keywords if kw in summary_lower)
    ratio = matches / max(len(field_keywords), 1)
    score = round(min(ratio, 1.0) * 100)

    if matches > 0:
        return {"score": score, "explanation": f"{matches} field keywords found in research summary"}
    return {"score": 0, "explanation": "No clear methods overlap detected"}


@router.get("/{professor_id}/fit-score")
async def get_professor_fit_score(
    professor_id: str,
    current_user: User = Depends(require_level(2)),
    db: Session = Depends(get_db),
):
    """Compute fit score between the current user and a professor.

    Returns 5 dimension scores (topic, activity, availability, funding, methods)
    and an overall weighted score.
    """
    try:
        professor = db.query(Professor).filter(Professor.id == UUID(professor_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid professor_id format")

    if not professor:
        raise HTTPException(status_code=404, detail="Professor not found")

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found — complete onboarding first")

    # Gather professor data
    prof_tags = professor.interests_tags if isinstance(professor.interests_tags, list) else []
    user_interests = profile.research_areas if isinstance(profile.research_areas, list) else []

    # Check enrichment cache for extra data (h_index, match_score)
    enrichment_data = None
    cache_match_score = None
    if professor.institution_id:
        cache_entry = (
            db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.entity_id == professor.institution_id,
                EnrichmentCache.freshness_bucket == "professor_matches:30d",
                EnrichmentCache.user_id == current_user.id,
                EnrichmentCache.expires_at > datetime.utcnow(),
            )
            .order_by(EnrichmentCache.computed_at.desc())
            .first()
        )
        if cache_entry and cache_entry.value_json:
            ranked = cache_entry.value_json.get("ranked_professors", [])
            for p in ranked:
                if (
                    p.get("openalex_id") == professor.openalex_id
                    or (p.get("name", "").lower() == (professor.full_name or "").lower())
                ):
                    enrichment_data = p
                    cache_match_score = p.get("match_score")
                    break

    h_index = None
    if enrichment_data:
        h_index = enrichment_data.get("h_index")

    # Count funding opportunities at institution
    funding_count = 0
    if professor.institution_id:
        funding_count = (
            db.query(func.count(FundingOpportunity.id))
            .filter(FundingOpportunity.institution_id == professor.institution_id)
            .scalar()
        ) or 0

    # Compute dimensions
    topic = _compute_topic_overlap(user_interests, prof_tags)
    activity = _compute_activity_score(h_index, enrichment_data)
    availability = _compute_availability_score(professor.is_accepting_students)
    funding = _compute_funding_score(funding_count)
    methods = _compute_methods_score(profile.primary_field_of_study, professor.research_summary)

    # Weighted overall (topic: 0.30, activity: 0.20, availability: 0.20, funding: 0.15, methods: 0.15)
    overall = round(
        topic["score"] * 0.30
        + activity["score"] * 0.20
        + availability["score"] * 0.20
        + funding["score"] * 0.15
        + methods["score"] * 0.15
    )

    return {
        "overall_score": overall,
        "dimensions": {
            "topic_overlap": topic,
            "research_activity": activity,
            "availability": availability,
            "funding": funding,
            "methods_alignment": methods,
        },
        "enrichment_match_score": cache_match_score,
        "funding_count": funding_count,
    }


@router.get("/{professor_id}/detail")
async def get_professor_detail(
    professor_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extended professor detail with enrichment data and funding info."""
    try:
        professor = db.query(Professor).filter(Professor.id == UUID(professor_id)).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid professor_id format")

    if not professor:
        raise HTTPException(status_code=404, detail="Professor not found")

    institution = professor.institution

    # Tags
    tags = []
    if professor.interests_tags and isinstance(professor.interests_tags, list):
        tags = professor.interests_tags
    else:
        research_tags = db.query(ProfessorResearchTag).filter(
            ProfessorResearchTag.professor_id == professor.id
        ).all()
        tags = [tag.tag for tag in research_tags]

    # Enrichment cache data
    enrichment_extra = {}
    if professor.institution_id:
        cache_entry = (
            db.query(EnrichmentCache)
            .filter(
                EnrichmentCache.entity_id == professor.institution_id,
                EnrichmentCache.freshness_bucket == "professor_matches:30d",
                EnrichmentCache.user_id == current_user.id,
                EnrichmentCache.expires_at > datetime.utcnow(),
            )
            .order_by(EnrichmentCache.computed_at.desc())
            .first()
        )
        if cache_entry and cache_entry.value_json:
            ranked = cache_entry.value_json.get("ranked_professors", [])
            for p in ranked:
                if (
                    p.get("openalex_id") == professor.openalex_id
                    or (p.get("name", "").lower() == (professor.full_name or "").lower())
                ):
                    enrichment_extra = {
                        "h_index": p.get("h_index"),
                        "citation_count": p.get("citation_count"),
                        "works_count": p.get("works_count"),
                        "match_score": p.get("match_score"),
                        "recent_papers": p.get("recent_papers", [])[:5],
                    }
                    break

    # Funding at institution
    funding_opportunities = []
    if professor.institution_id:
        fundings = (
            db.query(FundingOpportunity)
            .filter(FundingOpportunity.institution_id == professor.institution_id)
            .limit(10)
            .all()
        )
        for f in fundings:
            funding_opportunities.append({
                "id": str(f.id),
                "name": f.name,
                "type": f.funding_type,
                "amount": f.amount,
                "deadline": f.deadline.isoformat() if hasattr(f, "deadline") and f.deadline else None,
            })

    now = datetime.utcnow()
    last_updated = professor.last_scraped_at or professor.last_enriched_at
    is_stale = (now - last_updated > timedelta(days=30)) if last_updated else True

    return {
        "id": str(professor.id),
        "full_name": professor.full_name,
        "title": professor.title,
        "institution": {
            "id": str(institution.id) if institution else None,
            "name": institution.name if institution else None,
            "country": institution.country if institution else None,
            "city": institution.city if institution else None,
            "website_url": institution.website_url if institution else None,
        },
        "email": professor.email,
        "personal_page_url": professor.personal_page_url,
        "scholar_profile_url": professor.scholar_profile_url,
        "openalex_id": professor.openalex_id,
        "semantic_scholar_id": professor.semantic_scholar_id,
        "orcid_id": professor.orcid_id,
        "research_summary": professor.research_summary,
        "tags": tags,
        "is_accepting_students": professor.is_accepting_students,
        "enrichment": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "is_stale": is_stale,
            **enrichment_extra,
        },
        "funding_opportunities": funding_opportunities,
        "funding_count": len(funding_opportunities),
    }


@router.post("/{professor_id}/generate-email")
async def generate_email_draft(
    professor_id: str,
    program_id: Optional[str] = Query(None),
    current_user: User = Depends(require_level(3)),
    db: Session = Depends(get_db)
):
    """Generate a cold email draft for a professor.
    
    Args:
        professor_id: Professor to email
        program_id: Optional program context
    """
    try:
        professor = db.query(Professor).filter(Professor.id == UUID(professor_id)).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid professor_id format"
        )
    
    if not professor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professor not found"
        )
    
    # Load user profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    # Load academic record
    academic_record = db.query(AcademicRecord).filter(
        AcademicRecord.user_id == current_user.id
    ).order_by(AcademicRecord.end_year.desc().nullslast()).first()
    
    # Load program if provided
    program = None
    if program_id:
        try:
            program = db.query(Program).filter(Program.id == UUID(program_id)).first()
        except ValueError:
            pass  # Invalid program_id, just ignore
    
    # Generate email
    try:
        # Update profile with user name for email generation
        user_name = current_user.full_name or "Student"
        # Temporarily add user_name to profile object for email generation
        profile._user_name = user_name  # Store user name for use in generator
        subject, body = generate_cold_email(professor, profile, academic_record, program)
    except Exception as e:
        # Fallback to simple template
        user_name = current_user.full_name or "Student"
        user_field = profile.primary_field_of_study or "my field"
        subject, body = generate_email_template_simple(professor, user_name, user_field)
    
    # Store draft
    email_draft = OutreachEmail(
        user_id=current_user.id,
        professor_id=professor.id,
        program_id=program.id if program else None,
        subject=subject,
        body=body,
        generation_context=f"Generated for professor {professor.full_name}"
    )
    db.add(email_draft)
    db.commit()
    db.refresh(email_draft)
    
    return {
        "id": str(email_draft.id),
        "professor_id": str(professor.id),
        "professor_name": professor.full_name,
        "program_id": str(program.id) if program else None,
        "program_name": program.name if program else None,
        "subject": subject,
        "body": body,
        "created_at": email_draft.created_at.isoformat(),
    }


@router.get("/outreach/emails")
async def list_outreach_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all outreach email drafts for the current user."""
    emails = db.query(OutreachEmail).filter(
        OutreachEmail.user_id == current_user.id
    ).order_by(OutreachEmail.created_at.desc()).all()
    
    results = []
    for email in emails:
        professor = email.professor
        institution = professor.institution if professor else None
        program = email.program
        
        results.append({
            "id": str(email.id),
            "professor_id": str(email.professor_id) if email.professor_id else None,
            "professor_name": professor.full_name if professor else None,
            "institution_name": institution.name if institution else None,
            "program_id": str(email.program_id) if email.program_id else None,
            "program_name": program.name if program else None,
            "subject": email.subject,
            "created_at": email.created_at.isoformat(),
            "is_sent": email.is_sent,
        })
    
    return results


@router.get("/outreach/emails/{email_id}")
async def get_outreach_email(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific outreach email draft."""
    try:
        email = db.query(OutreachEmail).filter(
            OutreachEmail.id == UUID(email_id),
            OutreachEmail.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email_id format"
        )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found"
        )
    
    professor = email.professor
    institution = professor.institution if professor else None
    program = email.program
    
    return {
        "id": str(email.id),
        "professor_id": str(email.professor_id) if email.professor_id else None,
        "professor_name": professor.full_name if professor else None,
        "institution_name": institution.name if institution else None,
        "program_id": str(email.program_id) if email.program_id else None,
        "program_name": program.name if program else None,
        "subject": email.subject,
        "body": email.body,
        "created_at": email.created_at.isoformat(),
        "updated_at": email.updated_at.isoformat(),
        "is_sent": email.is_sent,
    }


@router.put("/outreach/emails/{email_id}")
async def update_outreach_email(
    email_id: str,
    subject: Optional[str] = Query(None),
    body: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an outreach email draft."""
    try:
        email = db.query(OutreachEmail).filter(
            OutreachEmail.id == UUID(email_id),
            OutreachEmail.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email_id format"
        )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found"
        )
    
    if subject:
        email.subject = subject
    if body:
        email.body = body
    
    db.commit()
    db.refresh(email)
    
    return {
        "id": str(email.id),
        "subject": email.subject,
        "body": email.body,
        "updated_at": email.updated_at.isoformat(),
    }


@router.delete("/outreach/emails/{email_id}")
async def delete_outreach_email(
    email_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an outreach email draft."""
    try:
        email = db.query(OutreachEmail).filter(
            OutreachEmail.id == UUID(email_id),
            OutreachEmail.user_id == current_user.id
        ).first()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email_id format"
        )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email draft not found"
        )
    
    db.delete(email)
    db.commit()
    
    return {"message": "Email draft deleted"}

