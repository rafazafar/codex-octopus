## Why

Operators need account-level expiry dates so imported or added accounts can age out automatically without being fully deactivated. The current accounts model has no expiry field, no way to edit expiry from `/accounts`, and no routing rule that excludes expired accounts while still letting operators review and extend them.

## What Changes

- Add account-level `expires_at` behavior for dashboard-managed accounts.
- Default expiry to 30 days after import/add when the incoming payload does not carry expiry data.
- Preserve portable import/export round-tripping of expiry when the payload includes it.
- Exclude expired accounts from normal routing/selection without mutating their lifecycle `status`.
- Add a focused dashboard API and UI flow for manually editing account expiry dates.

## Capabilities

### New Capabilities

- `account-expiry`: Account-level expiry dates for dashboard-managed accounts, including defaulting, portable round-tripping, manual editing, and soft routing enforcement.

### Modified Capabilities

- None.

## Impact

- Affected backend areas: `app/db/models.py`, account migrations, `app/modules/accounts/*`, and account-selection/routing logic.
- Affected dashboard APIs: `GET /api/accounts`, `POST /api/accounts/import`, `GET /api/accounts/export`, and new `PATCH /api/accounts/{account_id}/expiry`.
- Affected frontend areas: account schemas, account API client/hooks, list/detail UI, and account-flow tests.
