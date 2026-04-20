from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.modules.shared.schemas import DashboardModel

SystemHealthStatus = Literal["healthy", "warning", "critical"]
SystemHealthSeverity = Literal["warning", "critical"]
SystemHealthRiskLevel = Literal["warning", "danger", "critical"]


class SystemHealthMetrics(DashboardModel):
    total_accounts: int | None = Field(default=None)
    active_accounts: int | None = Field(default=None)
    unavailable_accounts: int | None = Field(default=None)
    unavailable_ratio: float | None = Field(default=None)
    request_count: int | None = Field(default=None)
    rate_limit_ratio: float | None = Field(default=None)
    projected_exhaustion_at: datetime | None = Field(default=None)
    risk_level: SystemHealthRiskLevel | None = Field(default=None)


class SystemHealthAlert(DashboardModel):
    code: str
    severity: SystemHealthSeverity
    title: str
    message: str
    href: str
    metrics: SystemHealthMetrics | None = None


class SystemHealthResponse(DashboardModel):
    status: SystemHealthStatus
    updated_at: datetime
    alert: SystemHealthAlert | None = None
