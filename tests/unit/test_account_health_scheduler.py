from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

import app.modules.accounts.auth_health_scheduler as auth_health_scheduler

pytestmark = pytest.mark.unit


def test_build_account_auth_health_scheduler_respects_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        account_health_check_interval_seconds=42,
        account_health_check_enabled=False,
        account_health_check_refresh_leeway_seconds=7,
    )
    monkeypatch.setattr(auth_health_scheduler, "get_settings", lambda: settings)

    scheduler = auth_health_scheduler.build_account_auth_health_scheduler()

    assert scheduler.interval_seconds == 42
    assert scheduler.enabled is False
    assert scheduler.refresh_leeway_seconds == 7


@pytest.mark.asyncio
async def test_account_auth_health_scheduler_runs_checker_once(monkeypatch: pytest.MonkeyPatch) -> None:
    accounts_repo = AsyncMock()
    checker = AsyncMock()
    checker.check_once = AsyncMock()

    class FakeSession:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    scheduler = auth_health_scheduler.AccountAuthHealthScheduler(
        interval_seconds=60,
        enabled=True,
        refresh_leeway_seconds=300,
    )
    leader = SimpleNamespace(try_acquire=AsyncMock(return_value=True))

    with (
        patch.object(auth_health_scheduler, "_get_leader_election", return_value=leader),
        patch.object(auth_health_scheduler, "get_background_session", FakeSession),
        patch.object(auth_health_scheduler, "AccountsRepository", return_value=accounts_repo),
        patch.object(auth_health_scheduler, "AccountAuthHealthChecker", return_value=checker),
    ):
        await scheduler._check_once()

    checker.check_once.assert_awaited_once()
