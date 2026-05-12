# Weighted Account Routing

## Objective

Prepare and execute a bounded implementation plan so account routing can be biased toward selected accounts by owner-defined tiers such as gold, silver, and bronze.

## Original Request

Steer or bias routing to certain accounts by labeling accounts with tiers like "gold, silver, bronze" so certain accounts are used significantly more than others.

## Intake Summary

- Input shape: `vague`
- Audience: owner/operators of the account routing system
- Authority: `requested`
- Proof type: `test`
- Completion proof: tests or simulation prove configured tier ratios bias route selection toward higher tiers within accepted tolerance, while existing routing behavior and constraints still pass.
- Likely misfire: implement labels without measurable traffic bias, or implement bias without preserving existing routing safety and fairness constraints.
- Blind spots considered:
  - Tier semantics chosen as weighted share, not priority fallback.
  - Config-driven ratios chosen so operators can change tier weights.
  - Undefined/unlabeled accounts should default to bronze so existing accounts remain usable at low share.
  - First tranche should stay inside routing internals and config contract unless Scout/Judge prove API or UI changes are required.
  - What evidence proves "significantly more" is correct.
- Existing plan facts:
  - Local live board selected.
  - Gold/silver/bronze should bias routing by weighted share.
  - Tier ratios should be config-driven rather than hardcoded policy.
  - Undefined/unlabeled accounts should default to bronze.
  - First tranche should avoid UI/API surface changes unless needed for routing internals.

## Goal Kind

`open_ended`

## Current Tranche

Discover the existing routing model and account configuration, create/update the needed OpenSpec change first, choose a safe weighted-share tier design with unlabeled accounts defaulting to bronze, implement successive verified slices inside routing internals and config contract, and audit that selected tiers receive the intended higher routing share without breaking existing routing behavior.

## Non-Negotiable Constraints

- Use OpenSpec as source of truth for behavior changes.
- Do not update feature or behavior docs under `docs/`.
- Do not edit `CHANGELOG.md` directly.
- Keep implementation bounded by active Worker tasks and verification.
- Treat UI/API changes as out of scope for the first tranche unless Scout/Judge show routing internals cannot support the outcome without them.

## Stop Rule

Stop only when a final audit proves the full original outcome is complete.

Do not stop after planning, discovery, or Judge selection if a safe Worker task can be activated.

## Canonical Board

Machine truth lives at:

`docs/goals/weighted-account-routing/state.yaml`

If this charter and `state.yaml` disagree, `state.yaml` wins for task status, active task, receipts, verification freshness, and completion truth.

## Run Command

```text
/goal Follow docs/goals/weighted-account-routing/goal.md.
```

## PM Loop

On every `/goal` continuation:

1. Read this charter.
2. Read `state.yaml`.
3. Work only on the active board task.
4. Assign Scout, Judge, Worker, or PM according to the task.
5. Write a compact task receipt.
6. Update the board.
7. Finish only with a Judge/PM audit receipt that maps receipts and verification back to the original user outcome and records `full_outcome_complete: true`.
