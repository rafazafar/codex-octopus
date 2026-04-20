## Context

The repo already exposes account status and aggregate depletion risk through dashboard-oriented payloads, and the app shell already owns persistent header/footer chrome. What is missing is a shell-oriented system-health summary that can drive one global incident bar across all protected pages.

Relevant existing surfaces:
- `frontend/src/App.tsx`
- `frontend/src/components/layout/app-header.tsx`
- `frontend/src/components/layout/status-bar.tsx`
- `app/modules/dashboard/service.py`
- `app/modules/request_logs/repository.py`

## Goals / Non-Goals

**Goals**
- show one persistent warning/critical incident bar on protected pages
- keep incident computation backend-owned
- use measurable signals already present in the system where possible
- keep v1 deterministic and low-noise

**Non-Goals**
- manual incident lifecycle management
- acknowledge, snooze, or dismiss controls
- per-account incidents in the global bar
- notification delivery outside the web UI

## Decisions

### 1) Add a dedicated `/api/system-health` endpoint

Decision:
- create a compact shell-focused health summary endpoint instead of reusing dashboard overview directly

Why:
- keeps alert rules server-side
- avoids coupling shell alert behavior to dashboard presentation payloads
- provides a stable contract for future reuse

Rejected:
- frontend-only derivation from dashboard queries

### 2) Mount the incident bar in the app shell

Decision:
- render the bar in `AppLayout`, below the sticky header and above page content

Why:
- guaranteed visibility on all protected routes
- matches current shared-layout architecture
- preserves page-local alert ownership within page components

### 3) Use three signal families for v1

Decision:
- compute alerts from:
  - account pool availability
  - aggregate depletion risk
  - recent normalized request-log status mix

Why:
- these directly capture the operator concern about system-wide routing failure
- account status and depletion already exist
- request-log status mix adds rate-limit-wave detection with one focused backend aggregate

### 4) Show only the highest-severity active alert

Decision:
- return at most one visible alert in the shell

Why:
- avoids stacked noisy global warnings
- keeps operator attention focused
- simplifies UI behavior and testing

## Alert Rules

Account status semantics:
- healthy: `active`
- unavailable: `rate_limited`, `quota_exceeded`, `paused`, `deactivated`

Critical alerts:
- `no_active_accounts`: `active_count == 0`
- `account_pool_collapse`: `active_count / total_count < 0.20`
- `capacity_exhaustion_risk`: aggregate depletion risk is `critical`

Warning alerts:
- `account_pool_degraded`: `active_count / total_count < 0.50`
- `capacity_risk`: aggregate depletion risk is `danger`
- `rate_limit_wave`: normalized recent `rate_limit` share exceeds threshold with minimum volume

Recommended initial rate-limit-wave thresholds:
- lookback: 15 minutes
- minimum volume: 50 requests
- threshold: `rate_limit_share >= 0.30`

V1 severity policy:
- `rate_limit_wave` is warning-only

## API Shape

```ts
type SystemHealthResponse = {
  status: "healthy" | "warning" | "critical";
  updatedAt: string;
  alert: null | {
    code: string;
    severity: "warning" | "critical";
    title: string;
    message: string;
    href: string;
    metrics?: {
      totalAccounts?: number;
      activeAccounts?: number;
      unavailableAccounts?: number;
      unavailableRatio?: number;
      requestCount?: number;
      rateLimitRatio?: number;
      projectedExhaustionAt?: string | null;
      riskLevel?: "warning" | "danger" | "critical";
    };
  };
};
```

## Risks / Trade-offs

- threshold tuning may need adjustment after real traffic observation
- rate-limit-wave alerts can be noisy without a minimum-volume guard
- reusing depletion inputs from dashboard logic is good, but the public contract should remain shell-focused and compact

## Migration Plan

1. add OpenSpec deltas
2. add backend system-health module and request-log aggregate
3. add shell bar and frontend polling hook
4. add focused backend/frontend tests
5. validate OpenSpec and run targeted suites
