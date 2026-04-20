from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.dependencies import SettingsContext, get_settings_context
from app.modules.onboarding.schemas import PublicOnboardingBootstrapResponse
from app.modules.settings.runtime_connect_address import resolve_runtime_connect_address

router = APIRouter(prefix="/api/public/onboarding", tags=["public"])


@router.get("", response_model=PublicOnboardingBootstrapResponse)
async def get_public_onboarding_bootstrap(
    request: Request,
    context: SettingsContext = Depends(get_settings_context),
) -> PublicOnboardingBootstrapResponse:
    settings = await context.service.get_settings()
    return PublicOnboardingBootstrapResponse(
        connect_address=resolve_runtime_connect_address(request),
        api_key_auth_enabled=settings.api_key_auth_enabled,
    )
