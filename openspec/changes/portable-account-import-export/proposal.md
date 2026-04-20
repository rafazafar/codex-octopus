## Why

The Accounts dashboard can only import a single `auth.json` object today, while users already have account backups from other account-management tools that export an array-based JSON format. That forces manual conversion and makes codex-lb a dead end for account portability.

## What Changes

- Add one format-aware account import flow that accepts both the current single-account `auth.json` payload and an external array-based portable account export.
- Add an authenticated account export endpoint that serializes all stored accounts into the external portable JSON format with reusable tokens.
- Make bulk imports transactional so invalid batches roll back completely instead of partially updating stored accounts.
- Preserve existing overwrite-vs-duplicate handling by continuing to use the dashboard `importWithoutOverwrite` setting during imports.

## Capabilities

### New Capabilities

- `account-portability`: Portable import/export behavior for dashboard-managed ChatGPT accounts, including multi-format import, bulk transactional semantics, and external-format export.

### Modified Capabilities

- None.

## Impact

- Affected backend areas: `app/modules/accounts`, `app/core/auth`, request-scoped DB transaction behavior during imports.
- Affected dashboard APIs: `POST /api/accounts/import`, new `GET /api/accounts/export`.
- Affected frontend areas: accounts API client, Accounts page toolbar/actions, import dialog copy, MSW mocks, and account hooks/tests.
