from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, UsageHistory
from app.modules.accounts.repository import AccountsRepository
from app.modules.request_logs.repository import NormalizedStatusCounts, RequestLogsRepository
from app.modules.usage.repository import AdditionalUsageRepository, UsageRepository


class SystemHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._accounts_repo = AccountsRepository(session)
        self._request_logs_repo = RequestLogsRepository(session)
        self._usage_repo = UsageRepository(session)
        self._additional_usage_repo = AdditionalUsageRepository(session)

    async def list_accounts(self) -> list[Account]:
        return await self._accounts_repo.list_accounts()

    async def latest_usage_by_account(self, window: str) -> dict[str, UsageHistory]:
        return await self._usage_repo.latest_by_account(window=window)

    async def bulk_usage_history_since(
        self,
        account_ids: list[str],
        window: str,
        since: datetime,
    ) -> dict[str, list[UsageHistory]]:
        return await self._usage_repo.bulk_history_since(account_ids, window, since)

    async def latest_additional_recorded_at(self) -> datetime | None:
        return await self._additional_usage_repo.latest_recorded_at()

    async def get_recent_normalized_status_counts(self, since: datetime) -> NormalizedStatusCounts:
        return await self._request_logs_repo.aggregate_normalized_status_counts_since(since)
