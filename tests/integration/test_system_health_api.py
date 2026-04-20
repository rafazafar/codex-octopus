from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.crypto import TokenEncryptor
from app.core.utils.time import naive_utc_to_epoch, utcnow
from app.db.models import Account, AccountStatus
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.request_logs.repository import RequestLogsRepository
from app.modules.usage.repository import UsageRepository

pytestmark = pytest.mark.integration


def _make_account(
    account_id: str,
    email: str,
    *,
    status: AccountStatus = AccountStatus.ACTIVE,
    plan_type: str = "plus",
) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=email,
        plan_type=plan_type,
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=utcnow(),
        status=status,
        deactivation_reason=None,
    )


@pytest.mark.asyncio
async def test_system_health_returns_healthy_when_pool_and_traffic_are_healthy(async_client, db_setup):
    now = utcnow()
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_healthy", "healthy@example.com"))
        for index in range(10):
            await logs_repo.add_log(
                account_id="acc_healthy",
                request_id=f"req_healthy_{index}",
                model="gpt-5.1",
                input_tokens=10,
                output_tokens=5,
                latency_ms=50,
                status="success",
                error_code=None,
                requested_at=now - timedelta(minutes=1),
            )

    response = await async_client.get("/api/system-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["alert"] is None


@pytest.mark.asyncio
async def test_system_health_returns_critical_when_no_active_accounts_remain(async_client, db_setup):
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        await accounts_repo.upsert(
            _make_account("acc_rate", "rate@example.com", status=AccountStatus.RATE_LIMITED)
        )
        await accounts_repo.upsert(
            _make_account("acc_quota", "quota@example.com", status=AccountStatus.QUOTA_EXCEEDED)
        )
        await accounts_repo.upsert(
            _make_account("acc_paused", "paused@example.com", status=AccountStatus.PAUSED)
        )

    response = await async_client.get("/api/system-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "critical"
    assert payload["alert"]["code"] == "no_active_accounts"
    assert payload["alert"]["metrics"]["activeAccounts"] == 0


@pytest.mark.asyncio
async def test_system_health_returns_critical_on_capacity_exhaustion_risk(async_client, db_setup):
    now = utcnow().replace(microsecond=0)
    reset_at = int(naive_utc_to_epoch(now + timedelta(minutes=5)))
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        usage_repo = UsageRepository(session)
        await accounts_repo.upsert(_make_account("acc_depletion", "depletion@example.com"))
        await usage_repo.add_entry(
            "acc_depletion",
            10.0,
            window="primary",
            window_minutes=60,
            reset_at=reset_at,
            recorded_at=now - timedelta(minutes=10),
        )
        await usage_repo.add_entry(
            "acc_depletion",
            95.0,
            window="primary",
            window_minutes=60,
            reset_at=reset_at,
            recorded_at=now - timedelta(minutes=1),
        )

    response = await async_client.get("/api/system-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "critical"
    assert payload["alert"]["code"] == "capacity_exhaustion_risk"
    assert payload["alert"]["metrics"]["riskLevel"] == "critical"


@pytest.mark.asyncio
async def test_system_health_returns_warning_on_rate_limit_wave(async_client, db_setup):
    now = utcnow()
    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        logs_repo = RequestLogsRepository(session)
        await accounts_repo.upsert(_make_account("acc_wave", "wave@example.com"))
        for index in range(60):
            status = "error" if index < 24 else "success"
            error_code = "rate_limit_exceeded" if index < 24 else None
            await logs_repo.add_log(
                account_id="acc_wave",
                request_id=f"req_wave_{index}",
                model="gpt-5.1",
                input_tokens=10,
                output_tokens=0,
                latency_ms=25,
                status=status,
                error_code=error_code,
                requested_at=now - timedelta(minutes=1),
            )

    response = await async_client.get("/api/system-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "warning"
    assert payload["alert"]["code"] == "rate_limit_wave"
    assert payload["alert"]["metrics"]["requestCount"] == 60
    assert payload["alert"]["metrics"]["rateLimitRatio"] == pytest.approx(0.4)
