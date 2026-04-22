## Why

The dashboard donut safe-line marker currently reuses the elapsed-window percentage from the single worst-risk account in each quota window. That makes the marker useful as a warning reference for one account, but misleading as a pooled pace signal for the whole donut.

Operators read the donut as an aggregate view of the account pool. The marker should therefore represent the pooled on-pace position for the visible accounts in that window while leaving depletion severity and exhaustion forecasting unchanged.

## What Changes

- Compute dashboard donut `safeUsagePercent` as a pooled weighted elapsed-window marker across the accounts in the relevant quota window.
- Weight each account by its actual quota capacity for that window when available.
- Fall back to plan multipliers only when quota capacity is unavailable, with `plus=1`, `team=1`, `pro=5`, and unknown plans defaulting to `1`.
- Keep depletion risk level, burn rate, and projected exhaustion derived from the most at-risk account so alert semantics do not change in the same rollout.

## Impact

- Specs: `openspec/specs/frontend-architecture/spec.md`
- Backend: dashboard depletion aggregation
- Frontend: existing donut marker wiring continues to use `safeUsagePercent`, but that field now means pooled pace instead of worst-account elapsed progress
- Tests: backend depletion aggregation and dashboard overview integration coverage
