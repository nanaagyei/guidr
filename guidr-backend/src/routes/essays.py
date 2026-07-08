"""Essay routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from src.db import get_db
from src.models.essay import Essay
from src.models.essay_version import EssayVersion
from src.models.essay_review import EssayReview
from src.models.user import User
from src.schemas.essay import (
    EssayCreate,
    EssayUpdate,
    EssayResponse,
    EssayVersionResponse,
    EssayReviewResponse
)
from src.dependencies.auth import get_current_user

router = APIRouter(prefix="/essays", tags=["essays"])


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


@router.get("", response_model=List[EssayResponse])
async def list_essays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all essays for the current user."""
    essays = db.query(Essay).filter(
        Essay.user_id == current_user.id
    ).order_by(Essay.updated_at.desc()).all()
    return essays


@router.post("", response_model=EssayResponse, status_code=status.HTTP_201_CREATED)
async def create_essay(
    essay_data: EssayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new essay with initial version."""
    word_count = count_words(essay_data.content)

    essay = Essay(
        user_id=current_user.id,
        title=essay_data.title,
        essay_type=essay_data.essay_type,
        target_program_id=essay_data.target_program_id,
        word_count=word_count,
    )

    db.add(essay)
    db.flush()

    # Create version 1
    version = EssayVersion(
        essay_id=essay.id,
        version_number=1,
        content=essay_data.content,
        word_count=word_count,
    )
    db.add(version)
    db.commit()
    db.refresh(essay)

    return essay


@router.get("/{essay_id}", response_model=dict)
async def get_essay(
    essay_id: UUID,
    include_versions: bool = False,
    include_reviews: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get essay details with optional versions and reviews."""
    essay = db.query(Essay).filter(
        Essay.id == essay_id,
        Essay.user_id == current_user.id
    ).first()

    if not essay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )

    response = {
        "id": essay.id,
        "title": essay.title,
        "essay_type": essay.essay_type,
        "word_count": essay.word_count,
        "created_at": essay.created_at,
        "updated_at": essay.updated_at,
    }

    if include_versions:
        versions = db.query(EssayVersion).filter(
            EssayVersion.essay_id == essay_id
        ).order_by(EssayVersion.version_number.desc()).all()
        response["versions"] = [
            {
                "id": v.id,
                "version_number": v.version_number,
                "content": v.content,
                "word_count": v.word_count,
                "created_at": v.created_at,
            }
            for v in versions
        ]

    if include_reviews:
        reviews = db.query(EssayReview).filter(
            EssayReview.essay_id == essay_id
        ).order_by(EssayReview.created_at.desc()).all()
        response["reviews"] = [
            {
                "id": r.id,
                "overall_score": float(r.overall_score) if r.overall_score else None,
                "clarity_score": float(r.clarity_score) if r.clarity_score else None,
                "structure_score": float(r.structure_score) if r.structure_score else None,
                "content_score": float(r.content_score) if r.content_score else None,
                "grammar_score": float(r.grammar_score) if r.grammar_score else None,
                "strengths": r.strengths,
                "weaknesses": r.weaknesses,
                "suggestions": r.suggestions,
                "detailed_feedback": r.detailed_feedback,
                "created_at": r.created_at,
            }
            for r in reviews
        ]

    return response


@router.put("/{essay_id}", response_model=EssayResponse)
async def update_essay(
    essay_id: UUID,
    essay_data: EssayUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update essay and create new version if content changed."""
    essay = db.query(Essay).filter(
        Essay.id == essay_id,
        Essay.user_id == current_user.id
    ).first()

    if not essay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )

    # Update title if provided
    if essay_data.title:
        essay.title = essay_data.title

    # If content changed, create new version
    if essay_data.content:
        # Get latest version
        latest_version = db.query(EssayVersion).filter(
            EssayVersion.essay_id == essay_id
        ).order_by(EssayVersion.version_number.desc()).first()

        # Only create new version if content actually changed
        if not latest_version or latest_version.content != essay_data.content:
            word_count = count_words(essay_data.content)
            new_version_number = (latest_version.version_number + 1) if latest_version else 1

            new_version = EssayVersion(
                essay_id=essay_id,
                version_number=new_version_number,
                content=essay_data.content,
                word_count=word_count,
            )
            db.add(new_version)

            essay.word_count = word_count

    db.commit()
    db.refresh(essay)

    return essay


@router.delete("/{essay_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_essay(
    essay_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an essay."""
    essay = db.query(Essay).filter(
        Essay.id == essay_id,
        Essay.user_id == current_user.id
    ).first()

    if not essay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )

    db.delete(essay)
    db.commit()


@router.post("/{essay_id}/review", response_model=dict)
async def request_review(
    essay_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request essay review (enqueue worker job)."""
    essay = db.query(Essay).filter(
        Essay.id == essay_id,
        Essay.user_id == current_user.id
    ).first()

    if not essay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )

    # Get latest version
    latest_version = db.query(EssayVersion).filter(
        EssayVersion.essay_id == essay_id
    ).order_by(EssayVersion.version_number.desc()).first()

    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Essay has no content to review"
        )

    # TODO: Enqueue worker job `essay.review`
    # For now, return success

    return {
        "status": "queued",
        "essay_id": str(essay_id),
        "message": "Review request queued"
    }
