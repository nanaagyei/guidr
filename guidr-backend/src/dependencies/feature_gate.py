"""Feature-gating dependency for FastAPI routes.

Usage::

    @router.post("/run")
    async def run_recommendations(
        current_user: User = Depends(require_level(2)),
        db: Session = Depends(get_db),
    ):
        ...

Returns the current User on success or raises 403 with an actionable payload.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.models.user_profile import UserProfile
from src.utils.profile_completion import calculate_profile_completion, FIELD_LABELS

_LEVEL_DESCRIPTIONS = {
    1: "Complete your basic profile (degree and field of study)",
    2: "Complete your targeting profile (research areas, preferred countries, and location)",
    3: "Add at least one academic record to your profile",
}


def require_level(min_level: int):
    """Return a FastAPI dependency that enforces a minimum profile completion level."""

    async def _check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        profile = (
            db.query(UserProfile)
            .filter(UserProfile.user_id == current_user.id)
            .first()
        )

        if profile:
            completion = calculate_profile_completion(profile, db)
        else:
            completion = {
                "level": 0,
                "missing_fields": ["intended_degree", "primary_field_of_study"],
            }

        if completion["level"] < min_level:
            missing_labels = [
                FIELD_LABELS.get(f, f) for f in completion["missing_fields"]
            ]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PROFILE",
                    "required_level": min_level,
                    "current_level": completion["level"],
                    "missing_fields": completion["missing_fields"],
                    "missing_labels": missing_labels,
                    "message": _LEVEL_DESCRIPTIONS.get(
                        min_level,
                        f"Complete your profile to Level {min_level} to access this feature.",
                    ),
                },
            )

        return current_user

    return _check
