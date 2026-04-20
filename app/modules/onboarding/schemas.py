from __future__ import annotations

from app.modules.shared.schemas import DashboardModel


class PublicOnboardingBootstrapResponse(DashboardModel):
    connect_address: str
    api_key_auth_enabled: bool
