"""Recommendation routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from src.db import get_db
from src.models.recommendation_session import RecommendationSession, RecommendationStatus
from src.models.recommendation_result import RecommendationResult
from src.models.user_profile import UserProfile
from src.models.academic_record import AcademicRecord
from src.models.user import User
from src.models.program import Program
from src.models.institution import Institution
from src.dependencies.auth import get_current_user
from src.utils.recommendation_engine import generate_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/request")
async def request_recommendations(
    trigger_source: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request a new recommendation session.
    
    Preconditions:
    - Profile completion score >= 60%
    - At least one academic record
    
    Returns:
        Session ID and status
    """
    # Check profile completion
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()
    
    if not profile or profile.profile_completion_score < 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complete your profile (60%+) and upload at least one transcript to get recommendations."
        )
    
    # Check for academic records
    academic_record = db.query(AcademicRecord).filter(
        AcademicRecord.user_id == current_user.id
    ).first()
    
    if not academic_record:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload at least one academic record (transcript) to get recommendations."
        )
    
    # Create profile snapshot
    profile_snapshot = {
        "intended_degree": profile.intended_degree,
        "primary_field_of_study": profile.primary_field_of_study,
        "secondary_fields": profile.secondary_fields,
        "preferred_countries": profile.preferred_countries,
        "program_style_preference": profile.program_style_preference,
        "funding_priority": profile.funding_priority,
    }
    
    # Create session
    session = RecommendationSession(
        user_id=current_user.id,
        trigger_source=trigger_source or "manual",
        input_profile_snapshot=profile_snapshot,
        status="pending"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Generate recommendations synchronously (for MVP, can be async later)
    try:
        generate_recommendations(db, str(session.id), str(current_user.id))
    except Exception as e:
        # Error already logged in generate_recommendations
        pass
    
    return {
        "session_id": str(session.id),
        "status": session.status
    }


@router.get("/latest")
async def get_latest_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the latest completed recommendation session.
    
    Returns:
        Session details with results
    """
    session = db.query(RecommendationSession).filter(
        RecommendationSession.user_id == current_user.id,
        RecommendationSession.status == "completed"
    ).order_by(RecommendationSession.created_at.desc()).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recommendation sessions found."
        )
    
    # Get results
    results = db.query(RecommendationResult).filter(
        RecommendationResult.recommendation_session_id == session.id
    ).order_by(RecommendationResult.rank.asc()).all()
    
    # Load program details
    program_results = []
    for result in results:
        program = db.query(Program).filter(Program.id == result.program_id).first()
        if program:
            institution = db.query(Institution).filter(Institution.id == program.institution_id).first()
            program_results.append({
                "program_id": str(result.program_id),
                "program_name": program.name,
                "institution_name": institution.name if institution else None,
                "institution_city": institution.city if institution else None,
                "institution_country": institution.country if institution else None,
                "score": float(result.score),
                "tier": result.tier,
                "explanation": result.explanation,
                "reason_features": result.reason_features,
                "rank": result.rank,
            })
    
    return {
        "session_id": str(session.id),
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "results": program_results
    }


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific recommendation session by ID.
    
    Returns:
        Session details with results
    """
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == UUID(session_id),
        RecommendationSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Get results if completed
    program_results = []
    if session.status == "completed":
        results = db.query(RecommendationResult).filter(
            RecommendationResult.recommendation_session_id == session.id
        ).order_by(RecommendationResult.rank.asc()).all()
        
        for result in results:
            program = db.query(Program).filter(Program.id == result.program_id).first()
            if program:
                institution = db.query(Institution).filter(Institution.id == program.institution_id).first()
                program_results.append({
                    "program_id": str(result.program_id),
                    "program_name": program.name,
                    "institution_name": institution.name if institution else None,
                    "institution_city": institution.city if institution else None,
                    "institution_country": institution.country if institution else None,
                    "score": float(result.score),
                    "tier": result.tier,
                    "explanation": result.explanation,
                    "reason_features": result.reason_features,
                    "rank": result.rank,
                })
    
    return {
        "session_id": str(session.id),
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "error_message": session.error_message,
        "results": program_results
    }


@router.get("/history")
async def get_recommendation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all recommendation sessions for the user.
    
    Returns:
        List of sessions with summary info
    """
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

