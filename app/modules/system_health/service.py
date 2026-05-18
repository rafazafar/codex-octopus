from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus
from app.modules.request_logs.repository import NormalizedStatusCounts
from app.modules.system_health.repository import SystemHealthRepository
from app.modules.system_health.schemas import SystemHealthAlert, SystemHealthMetrics, SystemHealthResponse

_RATE_LIMIT_LOOKBACK_MINUTES = 15
_RATE_LIMIT_MIN_REQUEST_COUNT = 50
_RATE_LIMIT_WARNING_RATIO = 0.30
_ACCOUNT_POOL_CRITICAL_ACTIVE_RATIO = 0.20
_ACCOUNT_POOL_WARNING_ACTIVE_RATIO = 0.50


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
        counts = await self._repository.get_recent_normalized_status_counts(
            now - timedelta(minutes=_RATE_LIMIT_LOOKBACK_MINUTES)
        )

        pool = _build_account_pool_snapshot(accounts)

        alert = (
            _build_no_active_accounts_alert(pool)
            or _build_account_pool_collapse_alert(pool)
            or _build_account_pool_degraded_alert(pool)
            or _build_rate_limit_wave_alert(counts)
        )
        if alert is None:
            return SystemHealthResponse(status="healthy", updated_at=now, alert=None)
        return SystemHealthResponse(status=alert.severity, updated_at=now, alert=alert)


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
