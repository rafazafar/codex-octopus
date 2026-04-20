from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_public_onboarding_bootstrap_returns_minimal_contract(async_client):
    response = await async_client.get("/api/public/onboarding")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "connectAddress": "testserver",
        "apiKeyAuthEnabled": False,
    }


@pytest.mark.asyncio
async def test_public_onboarding_bootstrap_reflects_api_key_auth_setting(async_client):
    update = await async_client.put(
        "/api/settings",
        json={
            "stickyThreadsEnabled": True,
            "preferEarlierResetAccounts": False,
            "totpRequiredOnLogin": False,
            "apiKeyAuthEnabled": True,
        },
    )
    assert update.status_code == 200

    response = await async_client.get("/api/public/onboarding")
    assert response.status_code == 200
    payload = response.json()
    assert payload["apiKeyAuthEnabled"] is True
    assert set(payload.keys()) == {"connectAddress", "apiKeyAuthEnabled"}
