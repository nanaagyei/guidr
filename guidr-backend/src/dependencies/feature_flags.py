"""Feature-flag dependencies for endpoints of features gated as "Coming soon".

Whole routers are mounted conditionally in ``src/main.py``. This module covers
single endpoints that live on an otherwise enabled router; with the flag off they
return the same 404 an unmounted path would.
"""
from fastapi import HTTPException, status

from src.config import settings


async def require_funding_api() -> None:
    """Return 404 unless ``settings.enable_funding_api`` is true.

    Raises:
        HTTPException: 404 ``Not Found``.
    """
    if not settings.enable_funding_api:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
