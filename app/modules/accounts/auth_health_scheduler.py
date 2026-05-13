from __future__ import annotations

import asyncio
import contextlib
import importlib
import logging
from dataclasses import dataclass, field
from typing import Protocol, cast

from app.core.config.settings import get_settings
from app.db.session import get_background_session
from app.modules.accounts.auth_health import AccountAuthHealthChecker
from app.modules.accounts.repository import AccountsRepository

logger = logging.getLogger(__name__)


class _LeaderElectionLike(Protocol):
    async def try_acquire(self) -> bool: ...


def _get_leader_election() -> _LeaderElectionLike:
    module = importlib.import_module("app.core.scheduling.leader_election")
    return cast(_LeaderElectionLike, module.get_leader_election())


@dataclass(slots=True)
class AccountAuthHealthScheduler:
    interval_seconds: int
    enabled: bool
    refresh_leeway_seconds: int
    _task: asyncio.Task[None] | None = None
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            await self._check_once()
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def _check_once(self) -> None:
        if not await _get_leader_election().try_acquire():
            return
        async with self._lock:
            try:
                async with get_background_session() as session:
                    accounts_repo = AccountsRepository(session)
                    checker = AccountAuthHealthChecker(
                        accounts_repo,
                        refresh_leeway_seconds=self.refresh_leeway_seconds,
                    )
                    result = await checker.check_once()
                    if result.deactivated_count or result.refreshed_count or result.transient_failure_count:
                        logger.info(
                            (
                                "Account auth-health check completed checked=%s refreshed=%s "
                                "deactivated=%s transient_failures=%s"
                            ),
                            result.checked_count,
                            result.refreshed_count,
                            result.deactivated_count,
                            result.transient_failure_count,
                        )
            except Exception:
                logger.exception("Account auth-health check loop failed")


def build_account_auth_health_scheduler() -> AccountAuthHealthScheduler:
    settings = get_settings()
    return AccountAuthHealthScheduler(
        interval_seconds=settings.account_health_check_interval_seconds,
        enabled=settings.account_health_check_enabled,
        refresh_leeway_seconds=settings.account_health_check_refresh_leeway_seconds,
    )
