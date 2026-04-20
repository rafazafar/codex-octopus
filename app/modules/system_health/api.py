from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import set_dashboard_error_format, validate_dashboard_session
from app.dependencies import SystemHealthContext, get_system_health_context
from app.modules.system_health.schemas import SystemHealthResponse

router = APIRouter(
    prefix="/api/system-health",
    tags=["dashboard"],
    dependencies=[Depends(validate_dashboard_session), Depends(set_dashboard_error_format)],
)


@router.get("", response_model=SystemHealthResponse)
async def get_system_health(
    context: SystemHealthContext = Depends(get_system_health_context),
) -> SystemHealthResponse:
    return await context.service.get_system_health()
