"""Profile completion score calculation with level-based unlocks."""
from typing import Any

from sqlalchemy.orm import Session

from src.models.academic_record import AcademicRecord
from src.models.user_profile import UserProfile

# Human-readable labels for missing fields
FIELD_LABELS: dict[str, str] = {
    "intended_degree": "Intended Degree",
    "primary_field_of_study": "Field of Study",
    "research_areas": "Research Areas",
    "preferred_countries": "Preferred Countries",
    "country_of_citizenship": "Country of Citizenship or Current Country",
    "academic_record": "Academic Record",
    "secondary_fields": "Secondary Fields",
    "preferred_cities": "Preferred Cities",
    "career_goals": "Career Goals",
    "funding_priority": "Funding Priority",
    "program_style_preference": "Program Style",
    "preferred_start_term": "Start Term",
    "preferred_start_year": "Start Year",
}

# Fields tracked for percentage calculation (each ~8-10%)
_TRACKED_FIELDS = [
    "intended_degree",
    "primary_field_of_study",
    "country_of_citizenship",
    "preferred_countries",
    "research_areas",
    "career_goals",
    "funding_priority",
    "program_style_preference",
    "preferred_start_term",
    "preferred_start_year",
    "secondary_fields",
    "academic_record",  # virtual — checked via DB query
]


def _has_value(val: Any) -> bool:
    """Return True if a field has a meaningful value."""
    if val is None:
        return False
    if isinstance(val, (list, dict)):
        return len(val) > 0
    if isinstance(val, str):
        return bool(val.strip())
    return True


def calculate_profile_completion(
    profile: UserProfile,
    db: Session,
) -> dict:
    """Compute profile completion with level-based unlock system.

    Returns:
        {
            "percent": int (0-100),
            "level": int (0-3),
            "missing_fields": list[str],  # fields needed for *next* level
            "unlocks": {
                "dashboard": bool,
                "recommendations": bool,
                "professors": bool,
                "funding": bool,
            },
        }
    """
    has_academic_record = (
        db.query(AcademicRecord)
        .filter(AcademicRecord.user_id == profile.user_id)
        .first()
        is not None
    )

    # --- Percentage (field coverage) ---
    filled = 0
    for field in _TRACKED_FIELDS:
        if field == "academic_record":
            if has_academic_record:
                filled += 1
        elif field == "country_of_citizenship":
            # Either citizenship or current_country counts
            if _has_value(profile.country_of_citizenship) or _has_value(profile.current_country):
                filled += 1
        else:
            if _has_value(getattr(profile, field, None)):
                filled += 1

    percent = round((filled / len(_TRACKED_FIELDS)) * 100)

    # --- Level determination ---
    # Level 1: basics — intended_degree + primary_field_of_study
    has_degree = _has_value(profile.intended_degree)
    has_field = _has_value(profile.primary_field_of_study)
    level_1 = has_degree and has_field

    # Level 2: targeting — Level 1 + research_areas(>=1) + preferred_countries(>=1) + citizenship/country
    has_research = _has_value(profile.research_areas)
    has_countries = _has_value(profile.preferred_countries)
    has_location = _has_value(profile.country_of_citizenship) or _has_value(profile.current_country)
    level_2 = level_1 and has_research and has_countries and has_location

    # Level 3: full — Level 2 + academic record
    level_3 = level_2 and has_academic_record

    if level_3:
        level = 3
    elif level_2:
        level = 2
    elif level_1:
        level = 1
    else:
        level = 0

    # --- Missing fields for next level ---
    missing: list[str] = []
    if level < 1:
        if not has_degree:
            missing.append("intended_degree")
        if not has_field:
            missing.append("primary_field_of_study")
    elif level < 2:
        if not has_research:
            missing.append("research_areas")
        if not has_countries:
            missing.append("preferred_countries")
        if not has_location:
            missing.append("country_of_citizenship")
    elif level < 3:
        if not has_academic_record:
            missing.append("academic_record")

    # --- Unlocks ---
    unlocks = {
        "dashboard": level >= 1,
        "recommendations": level >= 2,
        "funding": level >= 2,
        "professors": level >= 3,
    }

    return {
        "percent": percent,
        "level": level,
        "missing_fields": missing,
        "unlocks": unlocks,
    }


def calculate_profile_completion_score(
    profile: UserProfile,
    db: Session,
) -> int:
    """Backward-compatible wrapper returning just the integer score."""
    return calculate_profile_completion(profile, db)["percent"]
