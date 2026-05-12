## Why

Operators need a way to steer substantially more traffic toward selected upstream accounts without removing other healthy accounts from the pool. Current routing can weight by remaining capacity, but it cannot express owner preference such as "use these accounts much more often than those accounts."

## What Changes

- Add account routing tiers for `gold`, `silver`, and `bronze`.
- Treat accounts without a configured tier as `bronze` so existing accounts remain usable.
- Add config-driven tier weights so operators can tune how much more often higher tiers are selected.
- Apply tier weights to non-sticky account selection while preserving existing eligibility, quota, cooldown, health-tier, sticky-affinity, and failover behavior.
- Add routing tests or simulation coverage that proves configured weights bias selection within an accepted tolerance.

## Capabilities

### New Capabilities

- `account-routing`: Account selection, routing tiers, default tier behavior, and weighted-share routing requirements.

### Modified Capabilities

- None.

## Impact

- Affected backend areas: account persistence, account-to-balancer state mapping, balancer selection logic, runtime settings, and Alembic migrations.
- Affected verification: OpenSpec validation plus focused balancer and database model tests.
- Dashboard/API tier editing is intentionally out of scope for this first tranche unless implementation evidence proves the routing internals cannot support the outcome without it.
