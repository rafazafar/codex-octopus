from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from typing import Any

import pytest

from app.core.auth.refresh import RefreshError, TokenRefreshResult
from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus
from app.modules.accounts.auth_health import AccountAuthHealthChecker

pytestmark = pytest.mark.unit

_UNSET = object()


class _AccountsRepo:
    def __init__(self, accounts: list[Account]) -> None:
        self._accounts = accounts
        self.status_updates: list[dict[str, Any]] = []
        self.token_updates: list[dict[str, Any]] = []

    async def list_accounts(self) -> list[Account]:
        return list(self._accounts)

    async def get_by_id(self, account_id: str) -> Account | None:
        return next((account for account in self._accounts if account.id == account_id), None)

    async def update_status(
        self,
        account_id: str,
        status: AccountStatus,
        deactivation_reason: str | None = None,
        reset_at: int | None = None,
        blocked_at: int | None | object = _UNSET,
    ) -> bool:
        account = await self.get_by_id(account_id)
        if account is None:
            return False
        account.status = status
        account.deactivation_reason = deactivation_reason
        account.reset_at = reset_at
        if blocked_at is not _UNSET:
            account.blocked_at = blocked_at
        self.status_updates.append(
            {
                "account_id": account_id,
                "status": status,
                "deactivation_reason": deactivation_reason,
            }
        )
        return True

    async def update_tokens(
        self,
        account_id: str,
        access_token_encrypted: bytes,
        refresh_token_encrypted: bytes,
        id_token_encrypted: bytes,
        last_refresh: datetime,
        plan_type: str | None = None,
        email: str | None = None,
        chatgpt_account_id: str | None = None,
    ) -> bool:
        account = await self.get_by_id(account_id)
        if account is None:
            return False
        account.access_token_encrypted = access_token_encrypted
        account.refresh_token_encrypted = refresh_token_encrypted
        account.id_token_encrypted = id_token_encrypted
        account.last_refresh = last_refresh
        if plan_type is not None:
            account.plan_type = plan_type
        if email is not None:
            account.email = email
        if chatgpt_account_id is not None:
            account.chatgpt_account_id = chatgpt_account_id
        self.token_updates.append({"account_id": account_id, "plan_type": plan_type})
        return True


def _jwt_with_exp(expires_at: datetime) -> str:
    payload = {
        "exp": int(expires_at.timestamp()),
        "email": "user@example.com",
        "https://api.openai.com/auth": {
            "chatgpt_account_id": "workspace_acc",
            "chatgpt_plan_type": "plus",
        },
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"header.{encoded}.sig"


def _make_account(
    account_id: str,
    *,
    access_token: str,
    refresh_token: str,
    status: AccountStatus = AccountStatus.ACTIVE,
) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        chatgpt_account_id=f"workspace-{account_id}",
        email="user@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt(access_token),
        refresh_token_encrypted=encryptor.encrypt(refresh_token),
        id_token_encrypted=encryptor.encrypt(_jwt_with_exp(utcnow() + timedelta(days=1))),
        last_refresh=utcnow(),
        status=status,
        deactivation_reason=None,
    )


@pytest.mark.asyncio
async def test_health_check_deactivates_expired_access_token_without_refresh() -> None:
    account = _make_account(
        "acc_missing_refresh",
        access_token=_jwt_with_exp(utcnow() - timedelta(minutes=1)),
        refresh_token="",
    )
    repo = _AccountsRepo([account])
    checker = AccountAuthHealthChecker(repo, refresh_leeway_seconds=0)

    result = await checker.check_once()

    assert result.deactivated_count == 1
    assert account.status == AccountStatus.DEACTIVATED
    assert account.deactivation_reason == "Access token expired and refresh token missing - re-login required"


@pytest.mark.asyncio
async def test_health_check_refreshes_near_expiry_access_token_with_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_refresh(refresh_token: str) -> TokenRefreshResult:
        assert refresh_token == "refresh-old"
        return TokenRefreshResult(
            access_token="access-new",
            refresh_token="refresh-new",
            id_token=_jwt_with_exp(utcnow() + timedelta(days=1)),
            account_id="workspace-refreshed",
            plan_type="pro",
            email="updated@example.com",
        )

    monkeypatch.setattr("app.modules.accounts.auth_manager.refresh_access_token", _fake_refresh)
    account = _make_account(
        "acc_refresh",
        access_token=_jwt_with_exp(utcnow() + timedelta(seconds=30)),
        refresh_token="refresh-old",
    )
    repo = _AccountsRepo([account])
    checker = AccountAuthHealthChecker(repo, refresh_leeway_seconds=60)

    result = await checker.check_once()

    assert result.refreshed_count == 1
    assert repo.token_updates == [{"account_id": "acc_refresh", "plan_type": "pro"}]
    assert account.status == AccountStatus.ACTIVE


@pytest.mark.asyncio
async def test_health_check_keeps_active_on_transient_refresh_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_refresh(_: str) -> TokenRefreshResult:
        raise RefreshError("temporarily_unavailable", "try later", False)

    monkeypatch.setattr("app.modules.accounts.auth_manager.refresh_access_token", _fake_refresh)
    account = _make_account(
        "acc_transient",
        access_token=_jwt_with_exp(utcnow() - timedelta(minutes=1)),
        refresh_token="refresh-old",
    )
    repo = _AccountsRepo([account])
    checker = AccountAuthHealthChecker(repo, refresh_leeway_seconds=0)

    result = await checker.check_once()

    assert result.transient_failure_count == 1
    assert repo.status_updates == []
    assert account.status == AccountStatus.ACTIVE
