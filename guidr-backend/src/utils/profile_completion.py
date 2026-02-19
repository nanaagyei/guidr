"""Profile completion score calculation."""
from src.models.user_profile import UserProfile
from src.models.academic_record import AcademicRecord
from sqlalchemy.orm import Session


def calculate_profile_completion_score(
    profile: UserProfile,
    db: Session
) -> int:
    """Calculate profile completion score (0-100).
    
    Scoring breakdown:
    - intended_degree: 10%
    - primary_field_of_study: 20%
    - citizenship/current country: 10%
    - preferred_countries: 10%
    - academic_record exists: 40%
    - test_scores exist: 10% (future)
    
    Args:
        profile: UserProfile object
        db: Database session
        
    Returns:
        Completion score (0-100)
    """
    score = 0
    
    # intended_degree (10%)
    if profile.intended_degree:
        score += 10
    
    # primary_field_of_study (20%)
    if profile.primary_field_of_study:
        score += 20
    
    # citizenship/current country (10%)
    if profile.country_of_citizenship or profile.current_country:
        score += 10
    
    # preferred_countries (10%)
    if profile.preferred_countries and len(profile.preferred_countries) > 0:
        score += 10
    
    # academic_record exists (40%)
    academic_records = db.query(AcademicRecord).filter(
        AcademicRecord.user_id == profile.user_id
    ).all()
    if academic_records:
        score += 40
    
    # test_scores exist (10%) - future feature
    # For now, this is 0
    
    return min(score, 100)

