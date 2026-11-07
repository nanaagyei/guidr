"""Research-provider guard for FastAPI routes.

Attach to every endpoint that starts research, so that in production a request
fails with 503 before any row is created when no real provider is configured::

    @router.post("/run", dependencies=[Depends(require_research_provider)])
    async def run_research(...):
        ...
"""
from fastapi import HTTPException, status

from src.pipeline.research_gateway.service import research_provider_available

RESEARCH_UNAVAILABLE_DETAIL = {
    "code": "RESEARCH_UNAVAILABLE",
    "message": "Research is temporarily unavailable. Nothing was generated.",
}


async def require_research_provider() -> None:
    """Raise 503 if research would fall back to synthetic data.

    Raises:
        HTTPException: 503 with code ``RESEARCH_UNAVAILABLE``.
    """
    if not research_provider_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=RESEARCH_UNAVAILABLE_DETAIL,
        )
