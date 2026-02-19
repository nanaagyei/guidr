"""Academic records routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from src.db import get_db
from src.models.academic_record import AcademicRecord
from src.models.user_profile import UserProfile
from src.models.user import User
from src.schemas.academic_record import AcademicRecordCreate, AcademicRecordResponse
from src.dependencies.auth import get_current_user
from src.utils.gpa import normalize_gpa
from src.utils.profile_completion import calculate_profile_completion_score

router = APIRouter(prefix="/academic-records", tags=["academic-records"])


@router.get("", response_model=List[AcademicRecordResponse])
async def list_academic_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all academic records for the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of academic records
    """
    records = db.query(AcademicRecord).filter(
        AcademicRecord.user_id == current_user.id
    ).all()
    
    return records


@router.post("", response_model=AcademicRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_academic_record(
    record_data: AcademicRecordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new academic record.
    
    Args:
        record_data: Academic record data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created academic record
        
    Raises:
        HTTPException: If validation fails
    """
    # Validate degree level
    valid_degree_levels = ['bachelors', 'masters', 'phd', 'other']
    if record_data.degree_level not in valid_degree_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"degree_level must be one of: {', '.join(valid_degree_levels)}"
        )
    
    # Validate years
    if record_data.start_year and record_data.end_year:
        if record_data.start_year > record_data.end_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_year must be less than or equal to end_year"
            )
    
    # Calculate normalized GPA if provided
    normalized_gpa = None
    if record_data.gpa_value and record_data.gpa_scale:
        normalized_gpa = normalize_gpa(
            float(record_data.gpa_value),
            float(record_data.gpa_scale)
        )
    
    # Create record
    new_record = AcademicRecord(
        user_id=current_user.id,
        institution_name=record_data.institution_name,
        country=record_data.country,
        degree_level=record_data.degree_level,
        field_of_study=record_data.field_of_study,
        gpa_value=record_data.gpa_value,
        gpa_scale=record_data.gpa_scale,
        normalized_gpa=normalized_gpa,
        start_year=record_data.start_year,
        end_year=record_data.end_year,
        is_current=record_data.is_current,
        source="manual",
        notes=record_data.notes,
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Update profile completion score
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile:
        profile.profile_completion_score = calculate_profile_completion_score(profile, db)
        db.commit()
    
    return new_record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_academic_record(
    record_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an academic record.
    
    Args:
        record_id: ID of the record to delete
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If record not found or not owned by user
    """
    record = db.query(AcademicRecord).filter(
        AcademicRecord.id == record_id,
        AcademicRecord.user_id == current_user.id
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Academic record not found"
        )
    
    db.delete(record)
    db.commit()
    
    # Update profile completion score
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile:
        profile.profile_completion_score = calculate_profile_completion_score(profile, db)
        db.commit()

