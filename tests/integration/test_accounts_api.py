from __future__ import annotations

import base64
import json

import pytest

from app.core.auth import generate_unique_account_id

pytestmark = pytest.mark.integration


def _encode_jwt(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"header.{body}.sig"


def _make_auth_json(raw_account_id: str, email: str) -> dict:
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    return {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }


@pytest.mark.asyncio
async def test_import_and_list_accounts(async_client):
    email = "tester@example.com"
    raw_account_id = "acc_explicit"
    payload = {
        "email": email,
        "chatgpt_account_id": "acc_payload",
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "auth_json"
    assert data["importedCount"] == 1
    assert len(data["accounts"]) == 1
    assert data["accountId"] == expected_account_id
    assert data["email"] == email
    assert data["planType"] == "plus"

    list_response = await async_client.get("/api/accounts")
    assert list_response.status_code == 200
    accounts = list_response.json()["accounts"]
    assert any(account["accountId"] == expected_account_id for account in accounts)


@pytest.mark.asyncio
async def test_reactivate_missing_account_returns_404(async_client):
    response = await async_client.post("/api/accounts/missing/reactivate")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_pause_missing_account_returns_404(async_client):
    response = await async_client.post("/api/accounts/missing/pause")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_pause_account(async_client):
    email = "pause@example.com"
    raw_account_id = "acc_pause"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    expected_account_id = generate_unique_account_id(raw_account_id, email)
    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200

    pause = await async_client.post(f"/api/accounts/{expected_account_id}/pause")
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    accounts = await async_client.get("/api/accounts")
    assert accounts.status_code == 200
    data = accounts.json()["accounts"]
    matched = next((account for account in data if account["accountId"] == expected_account_id), None)
    assert matched is not None
    assert matched["status"] == "paused"


@pytest.mark.asyncio
async def test_list_accounts_omits_removed_routing_tier(async_client):
    email = "tier-api@example.com"
    raw_account_id = "acc_tier_api"
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        },
    }

    files = {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}
    import_response = await async_client.post("/api/accounts/import", files=files)
    assert import_response.status_code == 200

    accounts = await async_client.get("/api/accounts")
    row = next(account for account in accounts.json()["accounts"] if account["email"] == email)
    assert "routingTier" not in row


@pytest.mark.asyncio
async def test_delete_missing_account_returns_404(async_client):
    response = await async_client.delete("/api/accounts/missing")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "account_not_found"


@pytest.mark.asyncio
async def test_list_accounts_includes_openai_provider(async_client):
    auth_json = _make_auth_json("acc_provider_list", "provider-list@example.com")
    await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(auth_json), "application/json")},
    )

    response = await async_client.get("/api/accounts")

    assert response.status_code == 200
    row = next(item for item in response.json()["accounts"] if item["email"] == "provider-list@example.com")
    assert row["provider"] == "openai"


@pytest.mark.asyncio
async def test_import_kiro_account_persists_provider_fields(async_client):
    payload = {
        "provider": "kiro",
        "email": "kiro@example.com",
        "accessToken": "kiro-access",
        "refreshToken": "kiro-refresh",
        "authMethod": "idc",
        "clientId": "client-id",
        "clientSecret": "client-secret",
        "region": "us-east-1",
        "expiresAt": 1790000000,
        "machineId": "machine-123",
        "profileArn": "arn:aws:codewhisperer:us-east-1:123:profile/test",
    }

    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("kiro.json", json.dumps(payload), "application/json")},
    )

    assert response.status_code == 200
    assert response.json()["accounts"][0]["provider"] == "kiro"
    listing = await async_client.get("/api/accounts")
    row = next(item for item in listing.json()["accounts"] if item["email"] == "kiro@example.com")
    assert row["provider"] == "kiro"
