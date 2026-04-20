from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from app.core import usage as usage_core
from app.core.utils.time import utcnow
from app.core.usage.types import UsageWindowRow
from app.db.models import Account, AccountStatus, UsageHistory
from app.modules.dashboard.schemas import DepletionResponse
from app.modules.usage.depletion_service import compute_aggregate_depletion, compute_depletion_for_account
from app.modules.request_logs.repository import NormalizedStatusCounts
from app.modules.system_health.repository import SystemHealthRepository
from app.modules.system_health.schemas import SystemHealthAlert, SystemHealthMetrics, SystemHealthResponse

_RATE_LIMIT_LOOKBACK_MINUTES = 15
_RATE_LIMIT_MIN_REQUEST_COUNT = 50
_RATE_LIMIT_WARNING_RATIO = 0.30
_ACCOUNT_POOL_CRITICAL_ACTIVE_RATIO = 0.20
_ACCOUNT_POOL_WARNING_ACTIVE_RATIO = 0.50
_RISK_RANK = {"safe": 0, "warning": 1, "danger": 2, "critical": 3}
_PRIMARY_WINDOW_MINUTES = usage_core.default_window_minutes("primary") or 300
_SECONDARY_WINDOW_MINUTES = usage_core.default_window_minutes("secondary") or 10080


@dataclass(frozen=True, slots=True)
class _AccountPoolSnapshot:
    total: int
    active: int

    @property
    def unavailable(self) -> int:
        return max(0, self.total - self.active)

    @property
    def active_ratio(self) -> float:
        if self.total <= 0:
            return 1.0
        return self.active / self.total

    @property
    def unavailable_ratio(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.unavailable / self.total


class SystemHealthService:
    def __init__(self, repository: SystemHealthRepository) -> None:
        self._repository = repository

    async def get_system_health(self) -> SystemHealthResponse:
        now = utcnow().replace(microsecond=0)
        accounts = await self._repository.list_accounts()
        primary_usage = await self._repository.latest_usage_by_account("primary")
        secondary_usage = await self._repository.latest_usage_by_account("secondary")
        last_sync_at = await self._repository.latest_additional_recorded_at()
        counts = await self._repository.get_recent_normalized_status_counts(
            now - timedelta(minutes=_RATE_LIMIT_LOOKBACK_MINUTES)
        )

        pool = _build_account_pool_snapshot(accounts)
        depletion_primary, depletion_secondary = await _build_depletion_by_window(
            repository=self._repository,
            primary_usage=primary_usage,
            secondary_usage=secondary_usage,
            now=now,
        )
        depletion = _select_highest_risk_depletion(depletion_primary, depletion_secondary)
        updated_at = _latest_recorded_at(primary_usage, secondary_usage, last_sync_at) or now

        alert = (
            _build_no_active_accounts_alert(pool)
            or _build_account_pool_collapse_alert(pool)
            or _build_capacity_alert(depletion, severity="critical")
            or _build_account_pool_degraded_alert(pool)
            or _build_capacity_alert(depletion, severity="warning")
            or _build_rate_limit_wave_alert(counts)
        )
        if alert is None:
            return SystemHealthResponse(status="healthy", updated_at=updated_at, alert=None)
        return SystemHealthResponse(status=alert.severity, updated_at=updated_at, alert=alert)


def _build_account_pool_snapshot(accounts: list[Account]) -> _AccountPoolSnapshot:
    total = len(accounts)
    active = sum(1 for account in accounts if account.status == AccountStatus.ACTIVE)
    return _AccountPoolSnapshot(total=total, active=active)


def _build_pool_metrics(pool: _AccountPoolSnapshot) -> SystemHealthMetrics:
    return SystemHealthMetrics(
        total_accounts=pool.total,
        active_accounts=pool.active,
        unavailable_accounts=pool.unavailable,
        unavailable_ratio=round(pool.unavailable_ratio, 4),
    )


def _build_no_active_accounts_alert(pool: _AccountPoolSnapshot) -> SystemHealthAlert | None:
    if pool.total <= 0 or pool.active > 0:
        return None
    return SystemHealthAlert(
        code="no_active_accounts",
        severity="critical",
        title="No active accounts remain",
        message="Routing cannot use any configured accounts right now.",
        href="/accounts",
        metrics=_build_pool_metrics(pool),
    )


def _build_account_pool_collapse_alert(pool: _AccountPoolSnapshot) -> SystemHealthAlert | None:
    if pool.total <= 0 or pool.active_ratio >= _ACCOUNT_POOL_CRITICAL_ACTIVE_RATIO:
        return None
    return SystemHealthAlert(
        code="account_pool_collapse",
        severity="critical",
        title="Account pool collapse",
        message=f"{pool.unavailable} of {pool.total} accounts are unavailable. Routing capacity is at risk.",
        href="/accounts",
        metrics=_build_pool_metrics(pool),
    )


def _build_account_pool_degraded_alert(pool: _AccountPoolSnapshot) -> SystemHealthAlert | None:
    if pool.total <= 0 or pool.active_ratio >= _ACCOUNT_POOL_WARNING_ACTIVE_RATIO:
        return None
    return SystemHealthAlert(
        code="account_pool_degraded",
        severity="warning",
        title="Account availability is degraded",
        message=f"{pool.unavailable} of {pool.total} accounts are currently unavailable.",
        href="/accounts",
        metrics=_build_pool_metrics(pool),
    )


def _select_highest_risk_depletion(
    primary: DepletionResponse | None,
    secondary: DepletionResponse | None,
) -> DepletionResponse | None:
    candidates = [candidate for candidate in (primary, secondary) if candidate is not None]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _RISK_RANK.get(item.risk_level, 0),
            -(item.seconds_until_exhaustion or float("inf")),
        ),
    )


def _build_capacity_alert(
    depletion: DepletionResponse | None,
    *,
    severity: Literal["warning", "critical"],
) -> SystemHealthAlert | None:
    if depletion is None:
        return None
    if severity == "critical" and depletion.risk_level != "critical":
        return None
    if severity == "warning" and depletion.risk_level != "danger":
        return None
    code = "capacity_exhaustion_risk" if severity == "critical" else "capacity_risk"
    title = "Capacity exhaustion is imminent" if severity == "critical" else "Capacity risk is rising"
    message = (
        "Remaining system capacity is projected to exhaust soon."
        if severity == "critical"
        else "System-wide capacity is trending toward exhaustion."
    )
    return SystemHealthAlert(
        code=code,
        severity=severity,
        title=title,
        message=message,
        href="/dashboard",
        metrics=SystemHealthMetrics(
            projected_exhaustion_at=depletion.projected_exhaustion_at,
            risk_level=depletion.risk_level if depletion.risk_level in {"warning", "danger", "critical"} else None,
        ),
    )


def _build_rate_limit_wave_alert(counts: NormalizedStatusCounts) -> SystemHealthAlert | None:
    if counts.total < _RATE_LIMIT_MIN_REQUEST_COUNT:
        return None
    rate_limit_ratio = counts.rate_limit / counts.total if counts.total > 0 else 0.0
    if rate_limit_ratio < _RATE_LIMIT_WARNING_RATIO:
        return None
    return SystemHealthAlert(
        code="rate_limit_wave",
        severity="warning",
        title="Rate limit wave detected",
        message="Rate limiting is affecting a large share of recent traffic.",
        href="/dashboard",
        metrics=SystemHealthMetrics(
            request_count=counts.total,
            rate_limit_ratio=round(rate_limit_ratio, 4),
        ),
    )


async def _build_depletion_by_window(
    *,
    repository: SystemHealthRepository,
    primary_usage: dict[str, UsageHistory],
    secondary_usage: dict[str, UsageHistory],
    now: datetime,
) -> tuple[DepletionResponse | None, DepletionResponse | None]:
    primary_rows, secondary_rows = usage_core.normalize_weekly_only_rows(
        _rows_from_latest(primary_usage),
        _rows_from_latest(secondary_usage),
    )
    normalized_primary_ids = {row.account_id for row in primary_rows}
    all_account_ids = set(primary_usage.keys()) | set(secondary_usage.keys())

    pri_fetch_ids: list[str] = []
    sec_fetch_ids: list[str] = []
    pri_since = now
    sec_since = now
    pri_cutoffs: dict[str, datetime] = {}
    sec_cutoffs: dict[str, datetime] = {}
    weekly_only_ids: set[str] = set()
    weekly_only_history_sources: dict[str, str] = {}

    for account_id in all_account_ids:
        if account_id in normalized_primary_ids:
            usage_entry = primary_usage[account_id]
            acct_window = usage_entry.window_minutes if usage_entry.window_minutes else _PRIMARY_WINDOW_MINUTES
            acct_since = now - timedelta(minutes=acct_window)
            pri_fetch_ids.append(account_id)
            pri_cutoffs[account_id] = acct_since
            if acct_since < pri_since:
                pri_since = acct_since
            if account_id in secondary_usage:
                sec_entry = secondary_usage[account_id]
                sec_window = sec_entry.window_minutes if sec_entry.window_minutes else _SECONDARY_WINDOW_MINUTES
                sec_since_for_account = now - timedelta(minutes=sec_window)
                sec_fetch_ids.append(account_id)
                sec_cutoffs[account_id] = sec_since_for_account
                if sec_since_for_account < sec_since:
                    sec_since = sec_since_for_account
        elif account_id in primary_usage:
            weekly_only_ids.add(account_id)
            primary_entry = primary_usage[account_id]
            sec_entry = secondary_usage.get(account_id)
            use_primary_stream = _should_use_weekly_primary_history(primary_entry, sec_entry)
            weekly_only_history_sources[account_id] = "primary" if use_primary_stream else "secondary"
            current_entry = primary_entry if use_primary_stream else sec_entry
            acct_window = (
                current_entry.window_minutes
                if current_entry is not None and current_entry.window_minutes
                else _SECONDARY_WINDOW_MINUTES
            )
            acct_since = now - timedelta(minutes=acct_window)
            if use_primary_stream:
                pri_fetch_ids.append(account_id)
                pri_cutoffs[account_id] = acct_since
                if acct_since < pri_since:
                    pri_since = acct_since
            else:
                sec_fetch_ids.append(account_id)
                sec_cutoffs[account_id] = acct_since
                if acct_since < sec_since:
                    sec_since = acct_since
        else:
            sec_entry = secondary_usage[account_id]
            acct_window = sec_entry.window_minutes if sec_entry.window_minutes else _SECONDARY_WINDOW_MINUTES
            acct_since = now - timedelta(minutes=acct_window)
            sec_fetch_ids.append(account_id)
            sec_cutoffs[account_id] = acct_since
            if acct_since < sec_since:
                sec_since = acct_since

    all_pri_rows = (
        await repository.bulk_usage_history_since(pri_fetch_ids, "primary", pri_since) if pri_fetch_ids else {}
    )
    all_sec_rows = (
        await repository.bulk_usage_history_since(sec_fetch_ids, "secondary", sec_since) if sec_fetch_ids else {}
    )

    primary_history: dict[str, list[UsageHistory]] = {}
    secondary_history: dict[str, list[UsageHistory]] = {}

    for account_id in all_account_ids:
        if account_id in normalized_primary_ids:
            cutoff = pri_cutoffs[account_id]
            rows = [row for row in all_pri_rows.get(account_id, []) if row.recorded_at >= cutoff]
            if rows:
                primary_history[account_id] = rows
            if account_id in sec_cutoffs:
                secondary_cutoff = sec_cutoffs[account_id]
                secondary_rows_for_account = [
                    row for row in all_sec_rows.get(account_id, []) if row.recorded_at >= secondary_cutoff
                ]
                if secondary_rows_for_account:
                    secondary_history[account_id] = secondary_rows_for_account
        elif account_id in weekly_only_ids:
            source = weekly_only_history_sources[account_id]
            if source == "primary":
                cutoff = pri_cutoffs[account_id]
                rows = [row for row in all_pri_rows.get(account_id, []) if row.recorded_at >= cutoff]
            else:
                cutoff = sec_cutoffs[account_id]
                rows = [row for row in all_sec_rows.get(account_id, []) if row.recorded_at >= cutoff]
            if rows:
                secondary_history[account_id] = rows
        else:
            cutoff = sec_cutoffs[account_id]
            rows = [row for row in all_sec_rows.get(account_id, []) if row.recorded_at >= cutoff]
            if rows:
                secondary_history[account_id] = rows

    return _aggregate_depletion(primary_history, "primary", now), _aggregate_depletion(secondary_history, "secondary", now)


def _aggregate_depletion(
    history_by_account: dict[str, list[UsageHistory]],
    window: str,
    now: datetime,
) -> DepletionResponse | None:
    metrics = []
    for account_id, rows in history_by_account.items():
        metrics.append(
            compute_depletion_for_account(
                account_id=account_id,
                limit_name="standard",
                window=window,
                history=rows,
                now=now,
            )
        )
    aggregate = compute_aggregate_depletion(metrics)
    if aggregate is None:
        return None
    return DepletionResponse(
        risk=aggregate.risk,
        risk_level=aggregate.risk_level,
        burn_rate=aggregate.burn_rate,
        safe_usage_percent=aggregate.safe_usage_percent,
        projected_exhaustion_at=aggregate.projected_exhaustion_at,
        seconds_until_exhaustion=aggregate.seconds_until_exhaustion,
    )


def _rows_from_latest(latest: dict[str, UsageHistory]) -> list[UsageWindowRow]:
    return [
        UsageWindowRow(
            account_id=entry.account_id,
            used_percent=entry.used_percent,
            reset_at=entry.reset_at,
            window_minutes=entry.window_minutes,
            recorded_at=entry.recorded_at,
        )
        for entry in latest.values()
    ]


def _should_use_weekly_primary_history(
    primary_entry: UsageHistory,
    secondary_entry: UsageHistory | None,
) -> bool:
    return usage_core.should_use_weekly_primary(
        _usage_history_to_window_row(primary_entry),
        _usage_history_to_window_row(secondary_entry) if secondary_entry is not None else None,
    )


def _usage_history_to_window_row(entry: UsageHistory) -> UsageWindowRow:
    return UsageWindowRow(
        account_id=entry.account_id,
        used_percent=entry.used_percent,
        reset_at=entry.reset_at,
        window_minutes=entry.window_minutes,
        recorded_at=entry.recorded_at,
    )


def _latest_recorded_at(
    primary_usage: dict[str, UsageHistory],
    secondary_usage: dict[str, UsageHistory],
    additional_ts: datetime | None = None,
) -> datetime | None:
    timestamps = [
        entry.recorded_at
        for entry in list(primary_usage.values()) + list(secondary_usage.values())
        if entry.recorded_at is not None
    ]
    if additional_ts is not None:
        timestamps.append(additional_ts)
    return max(timestamps) if timestamps else None
