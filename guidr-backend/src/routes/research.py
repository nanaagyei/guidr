"""Internal research gateway endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.dependencies.auth import require_admin_user
from src.pipeline.research_gateway import ResearchGatewayService, ResearchRequest

router = APIRouter(prefix="/internal/research", tags=["research"])


@router.post("/run")
async def run_research(
    request: ResearchRequest,
    _: str = Depends(require_admin_user),
):
    """Execute a research job (URL_DISCOVERY, etc.). Internal use only."""
    service = ResearchGatewayService()
    return service.run(request).model_dump()
