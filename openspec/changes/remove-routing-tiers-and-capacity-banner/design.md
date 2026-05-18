## Context

Account routing tiers currently add `gold`, `silver`, and `bronze` labels to account payloads, expose an account update endpoint, apply configurable tier weights during capacity-weighted routing, and render tier controls in the accounts UI. The app shell also renders a global incident bar from `/api/system-health`, which surfaces account capacity warnings as a persistent banner.

## Goals / Non-Goals

**Goals:**

- Remove operator-visible account routing tiers from API payloads and UI.
- Remove tier weighting from capacity-weighted account selection.
- Remove tier weight settings and tests.
- Remove the global incident bar/banner from the app shell.

**Non-Goals:**

- Drop the existing `accounts.routing_tier` database column in this change.
- Remove service-tier enforcement for API keys. That is separate from account routing tiers.
- Remove system-health backend data unless it becomes unreachable dead code after UI cleanup.

## Decisions

- Ignore persisted routing-tier values instead of migrating the column away now. This keeps the change small and avoids migration-chain churn; a future cleanup can drop the column if desired.
- Keep capacity-weighted routing but base weights only on remaining capacity. This preserves the routing strategy while removing the tier multiplier.
- Remove the routing-tier account endpoint rather than making it a no-op. The tier system is being removed, so keeping the write path would preserve a misleading contract.
- Remove the global incident bar from layout composition. Page-local system-health components may remain only if still reachable and tested without the shell banner.

## Risks / Trade-offs

- Existing clients calling `PUT /api/accounts/{id}/routing-tier` will receive 404 after route removal -> accepted breaking change because the feature is being removed.
- Existing `routing_tier` database values remain unused -> mitigated by omitting the field from schemas and selection state.
- Tests that used tier behavior as routing-weight proof need replacement/removal -> keep capacity-weighted coverage based on plan capacity and remaining credits.
