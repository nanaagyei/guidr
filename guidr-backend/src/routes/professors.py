"""Professor routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from uuid import UUID
from src.db import get_db
from src.models.professor import Professor
from src.models.professor_research_tag import ProfessorResearchTag
from src.models.institution import Institution
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

