# Account Tier UI

## Objective

Add the dashboard and API surface needed for operators to set account routing tiers (`gold`, `silver`, `bronze`, or default) for the weighted account routing behavior already implemented.

## Original Request

Add the UI for configuring account tiers.

## Intake Summary

- Input shape: `specific`
- Audience: operators managing account routing in the dashboard
- Authority: `requested`
- Proof type: `test`
- Completion proof: accounts can be assigned routing tiers through the dashboard, the chosen tier persists, reads back correctly, and existing unlabeled/default accounts keep bronze behavior.
- Likely misfire: add only backend or only visual labels without an editable, persisted operator workflow.
- Blind spots considered:
  - The first slice should focus on account tier labels on the Accounts page.
  - Tier weight editing on Settings is useful but is not required for the first UI tranche unless Scout/Judge finds the account UI cannot be complete without it.
  - Existing weighted-routing OpenSpec artifacts and migration work should be preserved and extended, not duplicated.
- Existing plan facts:
  - Weighted routing backend already added `routing_tier`, config-driven weights, and bronze fallback.
  - User explicitly asked for the missing menu/UI.
  - Local live board selected.

## Goal Kind

`specific`

## Current Tranche

Discover the existing account dashboard/API/frontend patterns, update OpenSpec artifacts for account-tier UI/API behavior, implement a verified UI/API slice for setting per-account routing tiers, and audit the operator workflow end to end.

## Non-Negotiable Constraints

- Use OpenSpec as source of truth for behavior changes.
- Do not update feature or behavior docs under `docs/`.
- Do not edit `CHANGELOG.md` directly.
- Keep frontend design consistent with the existing dashboard.
- Verify backend tests, frontend tests, and browser-visible workflow when feasible.

## Stop Rule

Stop only when a final audit proves the operator can configure account tiers through the dashboard and the persisted tier affects the existing weighted-routing backend path.

Do not stop after planning or OpenSpec updates if a safe Worker task can implement the UI/API slice.

## Canonical Board

Machine truth lives at:

`docs/goals/account-tier-ui/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/account-tier-ui/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Work only on the active board task.
4. Assign Scout, Judge, Worker, or PM according to the task.
5. Write a compact task receipt.
6. Update the board.
7. Continue until a final audit records `full_outcome_complete: true`.
