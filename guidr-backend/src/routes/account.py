"""Account self-service routes: data export, password change and account deletion."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.config import settings
from src.db import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.schemas.account import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteAccountRequest,
)
from src.services import account_service
from src.utils.password import PasswordPolicyError

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/export")
async def export_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download everything stored about the signed-in user as JSON.

    The payload is personal data: it is returned only to its owner and never logged.
    """
    payload = account_service.build_export(db, current_user)
    filename = f"guidr-export-{datetime.utcnow():%Y%m%d}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the password after checking the current one.

    Applies the same strength, length and reuse rules as password reset.
    """
    try:
        account_service.change_password(
            db, current_user, request.current_password, request.new_password
        )
    except (account_service.InvalidPasswordError, PasswordPolicyError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ChangePasswordResponse(message="Password changed successfully")


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    request: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the signed-in user's data and anonymise the account (re-authenticated)."""
    try:
        account_service.delete_account(db, current_user, request.password)
    except account_service.InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Clear the session cookie exactly as POST /auth/logout does.
    response.delete_cookie(
        key="session",
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return None
