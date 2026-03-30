"""Recommendation engine for generating program recommendations."""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from src.models.user_profile import UserProfile
from src.models.academic_record import AcademicRecord
from src.models.program import Program
from src.models.institution import Institution
from src.models.recommendation_session import RecommendationSession, RecommendationStatus
from src.models.recommendation_result import RecommendationResult, RecommendationTier


def calculate_gpa_score(user_gpa: Optional[Decimal], program_min_gpa: Optional[Decimal] = None) -> float:
    """Calculate GPA match score (0-40 points).
    
    Args:
        user_gpa: User's normalized GPA (4.0 scale)
        program_min_gpa: Program's expected minimum GPA (if known)
        
    Returns:
        Score between 0 and 40
    """
    if not user_gpa:
        return 20.0  # Neutral score if GPA unknown
    
    # If program has no min GPA requirement, give moderate score
    if not program_min_gpa:
        return 30.0
    
    if user_gpa >= program_min_gpa:
        return 40.0
    else:
        diff = float(program_min_gpa - user_gpa)
        score = max(0.0, 40.0 - diff * 20.0)
        return score


def calculate_field_score(
    user_field: Optional[str],
    user_secondary_fields: Optional[List[str]],
    program_field: Optional[str]
) -> float:
    """Calculate field of study match score (0-30 points).
    
    Args:
        user_field: User's primary field of study
        user_secondary_fields: User's secondary fields
        program_field: Program's field of study
        
    Returns:
        Score between 0 and 30
    """
    if not program_field:
        return 15.0  # Neutral score
    
    if not user_field:
        return 10.0  # Low score if user field unknown
    
    program_field_lower = program_field.lower()
    user_field_lower = user_field.lower()
    
    # Exact match
    if user_field_lower == program_field_lower:
        return 30.0
    
    # Partial match (contains)
    if user_field_lower in program_field_lower or program_field_lower in user_field_lower:
        return 25.0
    
    # Check secondary fields
    if user_secondary_fields:
        for secondary_field in user_secondary_fields:
            secondary_lower = secondary_field.lower()
            if secondary_lower in program_field_lower or program_field_lower in secondary_lower:
                return 20.0
    
    # Check for related fields (simple keyword matching)
    related_keywords = {
        'computer science': ['cs', 'computing', 'software', 'programming'],
        'machine learning': ['ml', 'ai', 'artificial intelligence', 'data science'],
        'data science': ['statistics', 'analytics', 'ml', 'machine learning'],
    }
    
    for key, keywords in related_keywords.items():
        if key in user_field_lower:
            if any(kw in program_field_lower for kw in keywords):
                return 20.0
        if key in program_field_lower:
            if any(kw in user_field_lower for kw in keywords):
                return 20.0
    
    return 10.0  # Minimal match


def calculate_location_score(
    preferred_countries: Optional[List[str]],
    program_country: Optional[str]
) -> float:
    """Calculate location preference match score (0-20 points).
    
    Args:
        preferred_countries: User's preferred countries
        program_country: Program's country
        
    Returns:
        Score between 0 and 20
    """
    if not program_country:
        return 10.0  # Neutral score
    
    if not preferred_countries or len(preferred_countries) == 0:
        return 10.0  # Neutral if no preference
    
    program_country_lower = program_country.lower()
    for preferred in preferred_countries:
        if preferred.lower() == program_country_lower:
            return 20.0
    
    return 10.0  # Not in preferred list


def calculate_feature_score(
    user_preferences: Dict[str, Any],
    program: Program
) -> float:
    """Calculate program feature match score (0-10 points).
    
    Args:
        user_preferences: User's program preferences
        program: Program object
        
    Returns:
        Score between 0 and 10
    """
    score = 0.0
    
    # Program style preference
    user_style = user_preferences.get('program_style_preference')
    if user_style and program.research_or_coursework:
        if user_style == 'research' and program.research_or_coursework == 'research':
            score += 5.0
        elif user_style == 'coursework' and program.research_or_coursework == 'coursework':
            score += 5.0
        elif user_style == 'both' or program.research_or_coursework == 'mixed':
            score += 3.0
    
    # Funding priority (tuition consideration)
    funding_priority = user_preferences.get('funding_priority')
    if funding_priority == 'must_have' and program.tuition_estimate_per_year:
        # Lower tuition = higher score
        if float(program.tuition_estimate_per_year) < 20000:
            score += 5.0
        elif float(program.tuition_estimate_per_year) < 40000:
            score += 3.0
    
    return min(10.0, score)


def assign_tier(score: float) -> str:
    """Assign tier based on score.
    
    Args:
        score: Recommendation score (0-100)
        
    Returns:
        Tier string: 'dream', 'reach', 'target', or 'safety'
    """
    if score >= 90:
        return "dream"
    elif score >= 75:
        return "reach"
    elif score >= 55:
        return "target"
    else:
        return "safety"


def generate_explanation(
    program: Program,
    score_components: Dict[str, float],
    user_profile: UserProfile,
    academic_record: Optional[AcademicRecord]
) -> tuple[str, List[str]]:
    """Generate explanation text and reason features.
    
    Args:
        program: Program object
        score_components: Dictionary of score component values
        user_profile: User profile
        academic_record: User's academic record
        
    Returns:
        Tuple of (explanation text, list of reason features)
    """
    reasons = []
    
    # GPA explanation
    if academic_record and academic_record.normalized_gpa:
        gpa_score = score_components.get('gpa_score', 0)
        if gpa_score >= 35:
            reasons.append(f"Your GPA ({academic_record.normalized_gpa:.2f}) aligns well with program expectations")
        elif gpa_score >= 20:
            reasons.append(f"GPA ({academic_record.normalized_gpa:.2f}) is competitive")
    
    # Field match
    field_score = score_components.get('field_score', 0)
    if field_score >= 25:
        reasons.append(f"Strong field match: {user_profile.primary_field_of_study}")
    elif field_score >= 15:
        reasons.append(f"Relevant field: {program.field_of_study}")
    
    # Location
    location_score = score_components.get('location_score', 0)
    if location_score >= 18:
        if program.institution:
            reasons.append(f"Located in preferred country: {program.institution.country}")
    
    # Program style
    feature_score = score_components.get('feature_score', 0)
    if feature_score >= 5:
        if program.research_or_coursework:
            reasons.append(f"Program style matches preference: {program.research_or_coursework}")
    
    # Compose explanation
    if reasons:
        explanation = f"This program is a good fit because: {' '.join(reasons[:3])}"
    else:
        explanation = f"This program aligns with your academic background and preferences."
    
    return explanation, reasons


def score_program(
    program: Program,
    user_profile: UserProfile,
    academic_record: Optional[AcademicRecord]
) -> Dict[str, Any]:
    """Score a single program against user profile.
    
    Args:
        program: Program to score
        user_profile: User profile
        academic_record: User's academic record (latest/best)
        
    Returns:
        Dictionary with score, tier, explanation, and components
    """
    # Get user GPA (use normalized if available)
    user_gpa = None
    if academic_record and academic_record.normalized_gpa:
        user_gpa = academic_record.normalized_gpa
    
    # Calculate component scores
    gpa_score = calculate_gpa_score(user_gpa)
    field_score = calculate_field_score(
        user_profile.primary_field_of_study,
        user_profile.secondary_fields,
        program.field_of_study
    )
    location_score = calculate_location_score(
        user_profile.preferred_countries,
        program.institution.country if program.institution else None
    )
    
    user_prefs = {
        'program_style_preference': user_profile.program_style_preference,
        'funding_priority': user_profile.funding_priority,
    }
    feature_score = calculate_feature_score(user_prefs, program)
    
    # Total score
    total_score = min(100.0, gpa_score + field_score + location_score + feature_score)
    
    # Assign tier
    tier = assign_tier(total_score)
    
    # Generate explanation
    score_components = {
        'gpa_score': gpa_score,
        'field_score': field_score,
        'location_score': location_score,
        'feature_score': feature_score,
    }
    explanation, reason_features = generate_explanation(
        program, score_components, user_profile, academic_record
    )
    
    return {
        'score': total_score,
        'tier': tier,
        'explanation': explanation,
        'reason_features': reason_features,
        'score_components': score_components,
    }


def generate_recommendations(
    db: Session,
    session_id: str,
    user_id: str
) -> None:
    """Generate recommendations for a user and save to database.
    
    This function implements the worker job logic.
    
    Args:
        db: Database session
        session_id: Recommendation session ID
        user_id: User ID
    """
    from uuid import UUID
    
    # Load session
    session = db.query(RecommendationSession).filter(
        RecommendationSession.id == UUID(session_id),
        RecommendationSession.user_id == UUID(user_id)
    ).first()
    
    if not session:
        raise ValueError(f"Session {session_id} not found")
    
    if session.status == "completed":
        return  # Already completed
    
    # Update status to running
    session.status = "running"
    db.commit()
    
    try:
        # Load user profile
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == UUID(user_id)
        ).first()
        
        if not profile or profile.profile_completion_score < 60:
            raise ValueError("Profile incomplete or not found")
        
        # Load academic records (get best/latest)
        academic_records = db.query(AcademicRecord).filter(
            AcademicRecord.user_id == UUID(user_id)
        ).order_by(AcademicRecord.end_year.desc().nullslast()).all()
        
        if not academic_records:
            raise ValueError("No academic records found")
        
        # Use latest academic record
        academic_record = academic_records[0] if academic_records else None
        
        # Filter and fetch candidate programs
        query = db.query(Program).join(Institution)
        
        # Filter by degree level
        if profile.intended_degree:
            query = query.filter(Program.degree_level == profile.intended_degree)
        
        # Filter by field of study (loose match)
        if profile.primary_field_of_study:
            field_lower = profile.primary_field_of_study.lower()
            query = query.filter(
                Program.field_of_study.ilike(f'%{field_lower}%')
            )
        
        # Filter by preferred countries
        if profile.preferred_countries and len(profile.preferred_countries) > 0:
            query = query.filter(
                Institution.country.in_(profile.preferred_countries)
            )
        
        programs = query.all()
        
        if not programs:
            raise ValueError("No programs found matching criteria")
        
        # Score all programs
        scored_programs = []
        for program in programs:
            result = score_program(program, profile, academic_record)
            scored_programs.append({
                'program': program,
                **result
            })
        
        # Sort by score descending
        scored_programs.sort(key=lambda x: x['score'], reverse=True)
        
        # Select final recommendations (ensure tier variety)
        final_recommendations = []
        tier_counts = {"dream": 0, "reach": 0, "target": 0, "safety": 0}
        max_recommendations = 20
        
        # First pass: ensure minimum requirements
        min_target = 3
        min_reach = 1
        min_dream = 1
        
        for item in scored_programs:
            if len(final_recommendations) >= max_recommendations:
                break
            
            tier = item['tier']
            tier_counts[tier] += 1
            
            # Add if we need more of this tier or if we're just selecting top programs
            should_add = (
                (tier == "target" and tier_counts[tier] <= min_target) or
                (tier == "reach" and tier_counts[tier] <= min_reach) or
                (tier == "dream" and tier_counts[tier] <= min_dream) or
                len(final_recommendations) < 10  # Always include top 10
            )
            
            if should_add:
                final_recommendations.append(item)
        
        # Fill remaining slots with best available
        for item in scored_programs:
            if len(final_recommendations) >= max_recommendations:
                break
            if item not in final_recommendations:
                final_recommendations.append(item)
        
        # Persist results
        for rank, item in enumerate(final_recommendations, start=1):
            result = RecommendationResult(
                recommendation_session_id=session.id,
                program_id=item['program'].id,
                rank=rank,
                score=Decimal(str(item['score'])),
                tier=item['tier'],
                explanation=item['explanation'],
                reason_features=item['reason_features']
            )
            db.add(result)
        
        # Update session
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        # Handle failure
        session.status = "failed"
        session.error_message = str(e)
        session.completed_at = datetime.utcnow()
        db.commit()
        raise

