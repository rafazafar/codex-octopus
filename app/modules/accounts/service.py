from __future__ import annotations

import json
from datetime import date
from datetime import timedelta
from typing import cast

from pydantic import ValidationError

from app.core.auth import (
    generate_unique_account_id,
)
from app.core.auth.api_key_cache import get_api_key_cache
from app.core.cache.invalidation import NAMESPACE_API_KEY, get_cache_invalidation_poller
from app.core.crypto import TokenEncryptor
from app.core.utils.time import naive_utc_to_epoch, utcnow
from app.db.models import Account, AccountStatus
from app.modules.accounts.portable import (
    PortableAccountBatch,
    PortableImportFormat,
    build_portable_export_account,
    parse_portable_account_batch,
)
from app.modules.accounts.mappers import build_account_summaries, build_account_usage_trends
from app.modules.accounts.repository import AccountsRepository
from app.modules.accounts.schemas import (
    AccountAdditionalQuota,
    AccountAdditionalWindow,
    AccountImportResponse,
    AccountImportFormat,
    ImportedAccountSummary,
    AccountRequestUsage,
    AccountSummary,
    AccountTrendsResponse,
)
from app.modules.proxy.account_cache import get_account_selection_cache
from app.modules.usage.additional_quota_keys import get_additional_display_label_for_quota_key
from app.modules.usage.repository import AdditionalUsageRepository, UsageRepository
from app.modules.usage.updater import AdditionalUsageRepositoryPort, UsageUpdater

_SPARKLINE_DAYS = 7
_DETAIL_BUCKET_SECONDS = 3600  # 1h → 168 points


class InvalidAuthJsonError(Exception):
    pass


class AccountExportBundle:
    def __init__(self, *, filename: str, payload: bytes, exported_count: int) -> None:
        self.filename = filename
        self.payload = payload
        self.exported_count = exported_count


class AccountsService:
    def __init__(
        self,
        repo: AccountsRepository,
        usage_repo: UsageRepository | None = None,
        additional_usage_repo: AdditionalUsageRepository | AdditionalUsageRepositoryPort | None = None,
    ) -> None:
        self._repo = repo
        self._usage_repo = usage_repo
        self._additional_usage_repo = additional_usage_repo
        self._usage_updater = UsageUpdater(usage_repo, repo, additional_usage_repo) if usage_repo else None
        self._encryptor = TokenEncryptor()

    async def list_accounts(self) -> list[AccountSummary]:
        accounts = await self._repo.list_accounts()
        if not accounts:
            return []
        account_ids = [account.id for account in accounts]
        account_id_set = set(account_ids)
        primary_usage = await self._usage_repo.latest_by_account(window="primary") if self._usage_repo else {}
        secondary_usage = await self._usage_repo.latest_by_account(window="secondary") if self._usage_repo else {}
        request_usage_rows = await self._repo.list_request_usage_summary_by_account(account_ids)
        request_usage_by_account = {
            account_id: AccountRequestUsage(
                request_count=row.request_count,
                total_tokens=row.total_tokens,
                cached_input_tokens=row.cached_input_tokens,
                total_cost_usd=row.total_cost_usd,
            )
            for account_id, row in request_usage_rows.items()
        }
        additional_quotas_by_account: dict[str, list[AccountAdditionalQuota]] = {}
        additional_usage_repo = cast(AdditionalUsageRepository | None, self._additional_usage_repo)
        if additional_usage_repo:
            quota_keys = await additional_usage_repo.list_quota_keys(account_ids=account_ids)
            for quota_key in quota_keys:
                primary_entries = await additional_usage_repo.latest_by_account(quota_key, "primary")
                secondary_entries = await additional_usage_repo.latest_by_account(quota_key, "secondary")
                for account_id in (set(primary_entries) | set(secondary_entries)) & account_id_set:
                    primary_entry = primary_entries.get(account_id)
                    secondary_entry = secondary_entries.get(account_id)
                    reference_entry = primary_entry or secondary_entry
                    if reference_entry is None:
                        continue
                    additional_quotas_by_account.setdefault(account_id, []).append(
                        AccountAdditionalQuota(
                            quota_key=quota_key,
                            limit_name=reference_entry.limit_name,
                            metered_feature=reference_entry.metered_feature,
                            display_label=get_additional_display_label_for_quota_key(quota_key)
                            or reference_entry.limit_name,
                            primary_window=AccountAdditionalWindow(
                                used_percent=primary_entry.used_percent,
                                reset_at=primary_entry.reset_at,
                                window_minutes=primary_entry.window_minutes,
                            )
                            if primary_entry is not None
                            else None,
                            secondary_window=AccountAdditionalWindow(
                                used_percent=secondary_entry.used_percent,
                                reset_at=secondary_entry.reset_at,
                                window_minutes=secondary_entry.window_minutes,
                            )
                            if secondary_entry is not None
                            else None,
                        )
                    )
        for account_quota_list in additional_quotas_by_account.values():
            account_quota_list.sort(key=lambda quota: quota.display_label or quota.quota_key or quota.limit_name)

        return build_account_summaries(
            accounts=accounts,
            primary_usage=primary_usage,
            secondary_usage=secondary_usage,
            request_usage_by_account=request_usage_by_account,
            additional_quotas_by_account=additional_quotas_by_account,
            encryptor=self._encryptor,
        )

    async def get_account_trends(self, account_id: str) -> AccountTrendsResponse | None:
        account = await self._repo.get_by_id(account_id)
        if not account or not self._usage_repo:
            return None
        now = utcnow()
        since = now - timedelta(days=_SPARKLINE_DAYS)
        since_epoch = naive_utc_to_epoch(since)
        bucket_count = (_SPARKLINE_DAYS * 24 * 3600) // _DETAIL_BUCKET_SECONDS
        buckets = await self._usage_repo.trends_by_bucket(
            since=since,
            bucket_seconds=_DETAIL_BUCKET_SECONDS,
            account_id=account_id,
        )
        trends = build_account_usage_trends(buckets, since_epoch, _DETAIL_BUCKET_SECONDS, bucket_count)
        trend = trends.get(account_id)
        return AccountTrendsResponse(
            account_id=account_id,
            primary=trend.primary if trend else [],
            secondary=trend.secondary if trend else [],
        )

    async def import_account(self, raw: bytes) -> AccountImportResponse:
        try:
            batch = parse_portable_account_batch(raw)
        except (json.JSONDecodeError, ValidationError, UnicodeDecodeError, TypeError) as exc:
            raise InvalidAuthJsonError("Invalid auth.json payload") from exc
        saved_accounts = await self._persist_import_batch(batch)
        if saved_accounts and self._usage_repo and self._usage_updater:
            latest_usage = await self._usage_repo.latest_by_account(window="primary")
            await self._usage_updater.refresh_accounts(saved_accounts, latest_usage)
        if saved_accounts:
            get_account_selection_cache().invalidate()
        imported_accounts = [
            ImportedAccountSummary(
                account_id=saved.id,
                email=saved.email,
                plan_type=saved.plan_type,
                status=saved.status,
            )
            for saved in saved_accounts
        ]
        response = AccountImportResponse(
            format=_response_import_format(batch.format),
            imported_count=len(imported_accounts),
            accounts=imported_accounts,
        )
        if len(imported_accounts) == 1:
            imported = imported_accounts[0]
            response.account_id = imported.account_id
            response.email = imported.email
            response.plan_type = imported.plan_type
            response.status = imported.status
        return response

    async def export_accounts(self) -> AccountExportBundle:
        accounts = await self._repo.list_accounts()
        payload = [
            build_portable_export_account(
                stored_account_id=account.id,
                email=account.email,
                plan_type=account.plan_type,
                raw_account_id=account.chatgpt_account_id,
                id_token=self._encryptor.decrypt(account.id_token_encrypted),
                access_token=self._encryptor.decrypt(account.access_token_encrypted),
                refresh_token=self._encryptor.decrypt(account.refresh_token_encrypted),
                created_at=account.created_at,
                last_refresh_at=account.last_refresh,
            ).model_dump(mode="json")
            for account in accounts
        ]
        filename = f"codex_accounts_{date.today().isoformat()}.json"
        return AccountExportBundle(
            filename=filename,
            payload=json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"),
            exported_count=len(payload),
        )

    async def reactivate_account(self, account_id: str) -> bool:
        result = await self._repo.update_status(account_id, AccountStatus.ACTIVE, None, None, blocked_at=None)
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def pause_account(self, account_id: str) -> bool:
        result = await self._repo.update_status(account_id, AccountStatus.PAUSED, None, None, blocked_at=None)
        if result:
            get_account_selection_cache().invalidate()
        return result

    async def delete_account(self, account_id: str) -> bool:
        result = await self._repo.delete(account_id)
        if result:
            get_account_selection_cache().invalidate()
            get_api_key_cache().clear()
            poller = get_cache_invalidation_poller()
            if poller is not None:
                await poller.bump(NAMESPACE_API_KEY)
        return result

    async def _persist_import_batch(self, batch: PortableAccountBatch) -> list[Account]:
        saved_accounts: list[Account] = []
        async with self._repo.transaction():
            for portable_account in batch.accounts:
                email = portable_account.email
                raw_account_id = portable_account.raw_account_id
                account_id = generate_unique_account_id(raw_account_id, email)
                account = Account(
                    id=account_id,
                    chatgpt_account_id=raw_account_id,
                    email=email,
                    plan_type=portable_account.plan_type,
                    access_token_encrypted=self._encryptor.encrypt(portable_account.access_token),
                    refresh_token_encrypted=self._encryptor.encrypt(portable_account.refresh_token),
                    id_token_encrypted=self._encryptor.encrypt(portable_account.id_token),
                    last_refresh=portable_account.last_refresh_at or utcnow(),
                    status=AccountStatus.ACTIVE,
                    deactivation_reason=None,
                )
                saved_accounts.append(await self._repo.upsert(account, commit=False))
        return saved_accounts


def _response_import_format(format_value: PortableImportFormat) -> AccountImportFormat:
    if format_value is PortableImportFormat.PORTABLE_JSON:
        return AccountImportFormat.PORTABLE_JSON
    return AccountImportFormat.AUTH_JSON
