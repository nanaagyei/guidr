"""Profile routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db import get_db
from src.models.user_profile import UserProfile
from src.models.user import User
from src.schemas.profile import UserProfileUpdate, UserProfileResponse
from src.dependencies.auth import get_current_user
from src.utils.profile_completion import calculate_profile_completion_score

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or auto-create user profile.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User profile object
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile:
        # Auto-create empty profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    # Update completion score
    profile.profile_completion_score = calculate_profile_completion_score(profile, db)
    db.commit()
    db.refresh(profile)
    
    return profile


@router.put("", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile.
    
    Args:
        profile_data: Profile data to update
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated profile object
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update fields
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    # Validate intended_degree
    if profile.intended_degree and profile.intended_degree not in ['masters', 'phd']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="intended_degree must be 'masters' or 'phd'"
        )
    
    # Validate preferred_start_year
    if profile.preferred_start_year:
        from datetime import datetime
        current_year = datetime.now().year
        if profile.preferred_start_year < current_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="preferred_start_year must be current year or later"
            )
    
    # Update completion score
    profile.profile_completion_score = calculate_profile_completion_score(profile, db)
    
    db.commit()
    db.refresh(profile)
    
    return profile

