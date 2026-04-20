from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import DashboardOverviewResponse
from app.modules.dashboard.service import DashboardService
from app.modules.request_logs.repository import NormalizedStatusCounts, RequestLogsRepository


class SystemHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._dashboard_repo = DashboardRepository(session)
        self._request_logs_repo = RequestLogsRepository(session)

    async def get_dashboard_overview(self) -> DashboardOverviewResponse:
        return await DashboardService(self._dashboard_repo).get_overview()

    async def get_recent_normalized_status_counts(self, since: datetime) -> NormalizedStatusCounts:
        return await self._request_logs_repo.aggregate_normalized_status_counts_since(since)
