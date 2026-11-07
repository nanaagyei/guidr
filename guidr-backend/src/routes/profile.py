"""Profile routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.db import get_db
from src.models.user_profile import UserProfile
from src.models.user import User
from src.schemas.profile import (
    UserProfileUpdate,
    UserProfileResponse,
    ProfileCompletionResponse,
    AIResearchConsentUpdate,
    AIResearchConsentResponse,
)
from src.dependencies.auth import get_current_user
from src.utils.profile_completion import (
    calculate_profile_completion,
    calculate_profile_completion_score,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_response(profile: UserProfile, db: Session) -> UserProfileResponse:
    """Build a UserProfileResponse with completion data."""
    completion = calculate_profile_completion(profile, db)
    resp = UserProfileResponse.model_validate(profile)
    resp.completion = ProfileCompletionResponse(**completion)
    return resp


@router.get("/completion", response_model=ProfileCompletionResponse)
async def get_profile_completion(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get profile completion details with level-based unlocks."""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        return ProfileCompletionResponse(
            percent=0,
            level=0,
            missing_fields=["intended_degree", "primary_field_of_study"],
            unlocks={
                "dashboard": False,
                "recommendations": False,
                "professors": False,
                "funding": False,
            },
        )

    completion = calculate_profile_completion(profile, db)
    return ProfileCompletionResponse(**completion)


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get or auto-create user profile."""
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

    return _build_response(profile, db)


@router.put("", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
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

    return _build_response(profile, db)


def _consent_response(profile: UserProfile | None) -> AIResearchConsentResponse:
    consented_at = profile.ai_research_consent_at if profile else None
    return AIResearchConsentResponse(consented=consented_at is not None, consented_at=consented_at)


@router.get("/ai-research-consent", response_model=AIResearchConsentResponse)
async def get_ai_research_consent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return whether the user consented to sending research inputs to model providers."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    return _consent_response(profile)


@router.put("/ai-research-consent", response_model=AIResearchConsentResponse)
async def update_ai_research_consent(
    body: AIResearchConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record or withdraw consent to send research inputs to model providers.

    With consent, research areas, preferred countries and a coarse funding priority may be
    included in research prompts. Withdrawing clears the timestamp; later research runs on
    degree level and field of study only.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    if body.consent:
        if profile.ai_research_consent_at is None:
            profile.ai_research_consent_at = datetime.utcnow()
    else:
        profile.ai_research_consent_at = None
    db.commit()
    db.refresh(profile)
    return _consent_response(profile)
