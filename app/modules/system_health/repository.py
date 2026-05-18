from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account
from app.modules.accounts.repository import AccountsRepository
from app.modules.request_logs.repository import NormalizedStatusCounts, RequestLogsRepository


class SystemHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._accounts_repo = AccountsRepository(session)
        self._request_logs_repo = RequestLogsRepository(session)

    async def list_accounts(self) -> list[Account]:
        return await self._accounts_repo.list_accounts()

    async def get_recent_normalized_status_counts(self, since: datetime) -> NormalizedStatusCounts:
        return await self._request_logs_repo.aggregate_normalized_status_counts_since(since)
