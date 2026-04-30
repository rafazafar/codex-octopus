## Why

API keys can currently route through all available accounts or through an explicit account allowlist. Operators sometimes need the inverse: keep a key on the general account pool while avoiding one problematic or reserved account. Today that requires maintaining a full allowlist of every other account, which is fragile as accounts are added or removed.

## What Changes

- Extend API-key account assignment policy rows so each account can be explicitly `allow`ed or `exclude`d.
- Preserve existing allowlist behavior for current API keys and existing `api_key_accounts` rows.
- Add dashboard API fields for both allowed and excluded account IDs.
- Replace the edit-only checkbox picker with a create-and-edit tri-state picker:
  - blank = inherit/default pool,
  - tick = explicitly allow,
  - cross = explicitly exclude.
- Apply exclusions in proxy routing and HTTP bridge session reuse for API-key-authenticated traffic.
- Permit an empty final eligible account set as a valid admin policy; requests then fail through the normal no-account path.

## Capabilities

### Modified Capabilities

- `api-keys`
- `responses-api-compat`
- `frontend-architecture`

## Impact

- Affected backend areas: `app/db/models.py`, Alembic migrations, `app/modules/api_keys/*`, and API-key-aware proxy selection checks.
- Affected dashboard APIs: `POST /api/api-keys`, `GET /api/api-keys`, `PATCH /api/api-keys/{key_id}`.
- Affected frontend areas: API-key schemas, create/edit dialogs, account picker component, API-key tests/mocks.
