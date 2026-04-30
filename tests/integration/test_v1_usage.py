from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.utils.time import utcnow
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyCreateData, ApiKeysService, LimitRuleInput
from app.modules.request_logs.repository import RequestLogsRepository

pytestmark = pytest.mark.integration


async def _create_api_key(
    *,
    name: str,
    limits: list[LimitRuleInput] | None = None,
) -> tuple[str, str]:
    async with SessionLocal() as session:
        service = ApiKeysService(ApiKeysRepository(session))
        created = await service.create_key(
            ApiKeyCreateData(
                name=name,
                allowed_models=None,
                limits=limits or [],
            )
        )
    return created.id, created.key


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("headers", "expected_message"),
    [
        ({}, "Missing API key in Authorization header"),
        ({"Authorization": "Bearer invalid-key"}, "Invalid API key"),
    ],
)
async def test_v1_usage_requires_valid_bearer_key_when_global_auth_disabled(async_client, headers, expected_message):
    response = await async_client.get("/v1/usage", headers=headers)

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "invalid_api_key"
    assert payload["error"]["message"] == expected_message


@pytest.mark.asyncio
async def test_v1_usage_returns_zero_usage_for_key_without_logs(async_client):
    _, plain_key = await _create_api_key(name="zero-usage")

    response = await async_client.get("/v1/usage", headers={"Authorization": f"Bearer {plain_key}"})

    assert response.status_code == 200
    payload = response.json()
    daily_usage = payload.pop("daily_usage")
    assert daily_usage == {}
    assert payload == {
        "request_count": 0,
        "total_tokens": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": 0.0,
        "usage": {
            "1d": {
                "request_count": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "total_cost_usd": 0.0,
            },
            "7d": {
                "request_count": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "total_cost_usd": 0.0,
            },
            "30d": {
                "request_count": 0,
                "total_tokens": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "output_tokens": 0,
                "total_cost_usd": 0.0,
            },
        },
    }


@pytest.mark.asyncio
async def test_v1_usage_scopes_usage_to_authenticated_key_and_hides_limits(async_client):
    key_a_id, key_a = await _create_api_key(name="usage-key-a")
    key_b_id, _ = await _create_api_key(name="usage-key-b")

    now = utcnow()

    async with SessionLocal() as session:
        logs = RequestLogsRepository(session)
        await logs.add_log(
            account_id=None,
            api_key_id=key_a_id,
            request_id="req_v1_usage_a1",
            model="gpt-5.4",
            input_tokens=100,
            output_tokens=25,
            cached_input_tokens=20,
            latency_ms=100,
            status="success",
            error_code=None,
            requested_at=now - timedelta(minutes=2),
        )
        await logs.add_log(
            account_id=None,
            api_key_id=key_a_id,
            request_id="req_v1_usage_a2",
            model="gpt-5.4",
            input_tokens=10,
            output_tokens=5,
            cached_input_tokens=2,
            latency_ms=80,
            status="success",
            error_code=None,
            requested_at=now - timedelta(minutes=1),
        )
        await logs.add_log(
            account_id=None,
            api_key_id=key_a_id,
            request_id="req_v1_usage_a3",
            model="gpt-5.4",
            input_tokens=40,
            output_tokens=10,
            cached_input_tokens=4,
            latency_ms=80,
            status="success",
            error_code=None,
            requested_at=now - timedelta(days=2),
        )
        await logs.add_log(
            account_id=None,
            api_key_id=key_a_id,
            request_id="req_v1_usage_a4",
            model="gpt-5.4",
            input_tokens=30,
            output_tokens=5,
            cached_input_tokens=3,
            latency_ms=80,
            status="success",
            error_code=None,
            requested_at=now - timedelta(days=20),
        )
        await logs.add_log(
            account_id=None,
            api_key_id=key_a_id,
            request_id="req_v1_usage_a5",
            model="gpt-5.4",
            input_tokens=20,
            output_tokens=5,
            cached_input_tokens=2,
            latency_ms=80,
            status="success",
            error_code=None,
            requested_at=now - timedelta(days=40),
        )
        await logs.add_log(
            account_id=None,
            api_key_id=key_b_id,
            request_id="req_v1_usage_b1",
            model="gpt-5.4-mini",
            input_tokens=999,
            output_tokens=111,
            cached_input_tokens=50,
            latency_ms=90,
            status="success",
            error_code=None,
            requested_at=now - timedelta(minutes=3),
        )

    response = await async_client.get("/v1/usage", headers={"Authorization": f"Bearer {key_a}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_count"] == 5
    assert payload["total_tokens"] == 250
    assert payload["input_tokens"] == 200
    assert payload["cached_input_tokens"] == 31
    assert payload["output_tokens"] == 50
    assert payload["total_cost_usd"] > 0
    assert payload["usage"]["1d"]["request_count"] == 2
    assert payload["usage"]["1d"]["total_tokens"] == 140
    assert payload["usage"]["1d"]["input_tokens"] == 110
    assert payload["usage"]["1d"]["cached_input_tokens"] == 22
    assert payload["usage"]["1d"]["output_tokens"] == 30
    assert payload["usage"]["1d"]["total_cost_usd"] > 0
    assert payload["usage"]["7d"]["request_count"] == 3
    assert payload["usage"]["7d"]["total_tokens"] == 190
    assert payload["usage"]["7d"]["input_tokens"] == 150
    assert payload["usage"]["7d"]["cached_input_tokens"] == 26
    assert payload["usage"]["7d"]["output_tokens"] == 40
    assert payload["usage"]["7d"]["total_cost_usd"] > 0
    assert payload["usage"]["30d"]["request_count"] == 4
    assert payload["usage"]["30d"]["total_tokens"] == 225
    assert payload["usage"]["30d"]["input_tokens"] == 180
    assert payload["usage"]["30d"]["cached_input_tokens"] == 29
    assert payload["usage"]["30d"]["output_tokens"] == 45
    assert payload["usage"]["30d"]["total_cost_usd"] > 0
    daily_usage = payload["daily_usage"]
    assert len(daily_usage) == 3
    assert list(daily_usage) == sorted(daily_usage, key=lambda value: tuple(reversed(value.split("_"))))
    today = now.date().strftime("%d_%m_%Y")
    two_days_ago = (now - timedelta(days=2)).date().strftime("%d_%m_%Y")
    twenty_days_ago = (now - timedelta(days=20)).date().strftime("%d_%m_%Y")
    forty_days_ago = (now - timedelta(days=40)).date().strftime("%d_%m_%Y")
    assert daily_usage[today]["requests"] == 2
    assert daily_usage[today]["tokens"] == 118
    assert daily_usage[today]["cost_usd"] > 0
    assert daily_usage[two_days_ago]["requests"] == 1
    assert daily_usage[two_days_ago]["tokens"] == 46
    assert daily_usage[two_days_ago]["cost_usd"] > 0
    assert daily_usage[twenty_days_ago]["requests"] == 1
    assert daily_usage[twenty_days_ago]["tokens"] == 32
    assert daily_usage[twenty_days_ago]["cost_usd"] > 0
    assert forty_days_ago not in daily_usage
    assert "limits" not in payload


@pytest.mark.asyncio
async def test_v1_usage_still_works_when_global_api_key_auth_is_disabled(async_client):
    _, plain_key = await _create_api_key(name="self-usage-auth-disabled")

    response = await async_client.get("/v1/usage", headers={"Authorization": f"Bearer {plain_key}"})

    assert response.status_code == 200
