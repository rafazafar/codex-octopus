from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.core.auth import extract_id_token_claims
from app.core.auth.refresh import RefreshError
from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus
from app.modules.accounts.auth_manager import AuthManager
from app.modules.proxy.account_cache import get_account_selection_cache

logger = logging.getLogger(__name__)

REAUTH_REQUIRED_REASON = "Access token expired and refresh token missing - re-login required"


class AccountsRepositoryPort(Protocol):
    async def get_by_id(self, account_id: str) -> Account | None: ...

    async def list_accounts(self) -> list[Account]: ...

    async def update_status(
        self,
        account_id: str,
        status: AccountStatus,
        deactivation_reason: str | None = None,
        reset_at: int | None = None,
        blocked_at: int | None = None,
    ) -> bool: ...

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
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class AccountAuthHealthCheckResult:
    checked_count: int = 0
    refreshed_count: int = 0
    deactivated_count: int = 0
    transient_failure_count: int = 0


class AccountAuthHealthChecker:
    def __init__(self, repo: AccountsRepositoryPort, *, refresh_leeway_seconds: int) -> None:
        self._repo = repo
        self._refresh_leeway_seconds = max(0, refresh_leeway_seconds)
        self._encryptor = TokenEncryptor()
        self._auth_manager = AuthManager(repo)

    async def check_once(self) -> AccountAuthHealthCheckResult:
        accounts = await self._repo.list_accounts()
        checked_count = 0
        refreshed_count = 0
        deactivated_count = 0
        transient_failure_count = 0
        changed = False

        for account in accounts:
            if account.status in (AccountStatus.PAUSED, AccountStatus.DEACTIVATED):
                continue
            checked_count += 1
            access_token = _decrypt_token(self._encryptor, account.access_token_encrypted)
            expires_at = _access_token_expires_at(access_token)
            if expires_at is None:
                continue
            threshold = utcnow() + timedelta(seconds=self._refresh_leeway_seconds)
            if expires_at > threshold:
                continue

            refresh_token = _decrypt_token(self._encryptor, account.refresh_token_encrypted)
            if not refresh_token:
                updated = await self._repo.update_status(
                    account.id,
                    AccountStatus.DEACTIVATED,
                    REAUTH_REQUIRED_REASON,
                    None,
                    blocked_at=None,
                )
                if updated:
                    account.status = AccountStatus.DEACTIVATED
                    account.deactivation_reason = REAUTH_REQUIRED_REASON
                    deactivated_count += 1
                    changed = True
                continue

            try:
                await self._auth_manager.refresh_account(account)
            except RefreshError as exc:
                if exc.is_permanent:
                    deactivated_count += 1
                    changed = True
                else:
                    transient_failure_count += 1
                    logger.warning(
                        "Account auth-health refresh failed transiently account_id=%s code=%s",
                        account.id,
                        exc.code,
                    )
                continue
            refreshed_count += 1
            changed = True

        if changed:
            get_account_selection_cache().invalidate()
        return AccountAuthHealthCheckResult(
            checked_count=checked_count,
            refreshed_count=refreshed_count,
            deactivated_count=deactivated_count,
            transient_failure_count=transient_failure_count,
        )


def _decrypt_token(encryptor: TokenEncryptor, encrypted: bytes | None) -> str | None:
    if not encrypted:
        return None
    try:
        return encryptor.decrypt(encrypted)
    except Exception:
        return None


def _access_token_expires_at(token: str | None) -> datetime | None:
    if not token:
        return None
    exp = extract_id_token_claims(token).exp
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
    if isinstance(exp, str) and exp.isdigit():
        return datetime.fromtimestamp(int(exp), tz=timezone.utc).replace(tzinfo=None)
    return None
