## Context

Account selection currently flows from persisted `Account` rows through `LoadBalancer._state_from_account()` into `AccountState`, then `select_account()` applies availability, health-tier, sticky-affinity, and routing-strategy logic. The default `capacity_weighted` strategy already uses probability proportional to remaining secondary credits, so the smallest compatible design is to multiply that existing capacity signal by an operator-controlled routing-tier weight.

Existing accounts do not have routing labels. The user chose weighted share semantics, config-driven ratios, routing-internals scope for the first tranche, and bronze default for undefined accounts.

## Goals / Non-Goals

**Goals:**

- Persist or otherwise carry an account routing tier into balancer state.
- Support `gold`, `silver`, and `bronze` routing tiers.
- Treat missing or unknown account tier values as `bronze`.
- Let operators configure tier weights without code changes.
- Bias `capacity_weighted` non-sticky selection by tier weight while preserving existing eligibility and safety filters.
- Prove selection distribution with deterministic tests or simulation tolerance.

**Non-Goals:**

- Dashboard UI for editing account tiers.
- Dashboard API endpoints for changing account tiers.
- Changing sticky-affinity semantics.
- Replacing capacity-aware routing with a separate priority queue.

## Decisions

1. Store the account tier on the account model.

   Rationale: account tiers are account attributes. Storing the label with the account keeps the behavior stable across process restarts and avoids brittle config maps keyed by account ID or email. Missing values still resolve to bronze in runtime logic, preserving compatibility for old rows and imports.

   Alternative considered: settings-only account ID to tier map. This would avoid a migration, but it would not truly label accounts and would become fragile when accounts are imported, deleted, or regenerated.

2. Keep tier ratios in runtime settings.

   Rationale: weights are policy, not account identity. Runtime settings already support typed environment configuration and are suitable for the first tranche because dashboard editing is out of scope.

   Alternative considered: dashboard settings row. This would make the policy editable at runtime, but it expands API/UI/storage scope beyond the first tranche.

3. Apply tier weights only inside `capacity_weighted` selection.

   Rationale: the current default strategy already expresses weighted probabilistic routing. Multiplying remaining capacity by tier weight preserves existing capacity behavior while allowing owner preference. Existing `usage_weighted` and `round_robin` behavior stays unchanged.

   Alternative considered: add a fourth routing strategy. That would require operators to change strategies and would duplicate much of the current capacity-weighted behavior.

## Risks / Trade-offs

- Migration adds account schema surface before UI editing exists → keep the column nullable or default-compatible and verify existing model tests.
- Very large gold weights could overuse gold accounts → preserve existing usage, cooldown, quota, and health-tier filters before weighting.
- Sticky traffic may not match configured distribution → specify and test non-sticky routing; sticky affinity remains intentionally stable.
- Unknown tier values could create surprising routing behavior → normalize unknown and missing tiers to bronze and cover that case in tests.

## Migration Plan

1. Add account-tier persistence with backward-compatible bronze resolution for existing rows.
2. Add runtime tier-weight setting with conservative defaults such as gold > silver > bronze.
3. Map account tier into `AccountState`.
4. Multiply capacity-weighted selection weights by the normalized tier weight.
5. Add tests for distribution, bronze default, unknown-tier fallback, zero/invalid weights, and existing capacity fallback behavior.
6. Roll back by setting all tier weights equal or reverting the migration/code slice before exposing an editing surface.
