## Context

`POST /api/accounts/import` currently parses one `auth.json` object, derives account identity from token claims, persists the account immediately, and optionally refreshes usage. The user wants codex-lb to accept a second, array-based portable format exported by another account-management app, and also export accounts back out in that same shared format.

The current import service mixes payload parsing and persistence, and `AccountsRepository.upsert()` commits per record. That is fine for single-account imports, but it cannot guarantee all-or-nothing behavior for batch imports. The frontend also assumes import means a single `auth.json` file and has no export action today.

## Goals / Non-Goals

**Goals:**

- Preserve one import entry point while auto-detecting both supported payload formats.
- Normalize both formats into one typed internal account-transfer model before persistence.
- Make bulk imports transactional with full rollback on any invalid record.
- Export all accounts in the external portable JSON shape with reusable tokens.
- Preserve the current `importWithoutOverwrite` behavior and avoid DB schema changes.

**Non-Goals:**

- Importing quota snapshots, tags, usage history, or third-party metadata into codex-lb state.
- Adding a preview wizard, selective export, or partial-success import mode.
- Changing account-selection or runtime routing behavior outside explicit import/export actions.

## Decisions

### Use a typed portable-account normalization layer

Create a small internal portable-account model plus format-specific adapters:

- current `auth.json` object -> portable account record
- external array record -> portable account record
- stored DB account -> external export record

This keeps parsing/mapping separate from DB writes and lets import and export share one normalization boundary.

**Alternative considered:** extend `AccountsService.import_account(raw)` with more branching. Rejected because format detection, per-record mapping, and persistence would remain tightly coupled and harder to test.

### Keep persistence inside `AccountsService`/`AccountsRepository`

The normalization layer should only produce validated account-transfer records. Token encryption, account ID generation, merge-vs-duplicate behavior, cache invalidation, and post-import usage refresh remain owned by the existing accounts service/repository path.

**Alternative considered:** move import persistence into a new standalone importer service. Rejected because it would duplicate existing account-write behavior and drift from the current merge/identity rules.

### Refactor repository writes to support caller-owned transactions

Batch imports need one transaction spanning every imported record. `AccountsRepository.upsert()` should therefore support non-autocommit writes so `AccountsService` can open one transaction, persist all records, then commit once. Post-commit usage refresh stays outside the atomic batch because it can trigger additional network and DB side effects unrelated to import validity.

**Alternative considered:** validate then call the current autocommit `upsert()` in a loop. Rejected because a mid-batch persistence error would still leave earlier rows committed.

### Export in the external array format with stable defaults

The export payload should match the external array shape closely enough for reuse by other tooling, while only populating fields codex-lb can derive confidently:

- fill stored identity/token fields and created timestamps
- use fixed/default values for stable format markers (`auth_mode`, `api_provider_mode`)
- emit `null` for unsupported metadata (`organization_id`, `quota`, tags, etc.)

This preserves interchange without inventing new local state just to satisfy third-party metadata.

## Risks / Trade-offs

- **Compatibility drift with the external app's undocumented fields** -> Keep import tolerant with `extra="ignore"` and export a stable subset plus nullable placeholders.
- **Response-contract churn for `/api/accounts/import`** -> Return a summary object with batch fields while preserving single-account convenience fields for existing callers/tests.
- **Longer import requests for large batches** -> Validate eagerly, write in one transaction, and keep post-commit refresh outside the atomic section.
- **Sensitive exports contain live tokens** -> Add explicit dashboard copy warning and keep the endpoint behind existing dashboard auth.

## Migration Plan

1. Add OpenSpec proposal/spec/design/tasks for the new `account-portability` capability.
2. Implement portable payload parsing and transactional import/export behavior in the accounts module.
3. Update the dashboard API client and Accounts page/actions for import/export UX.
4. Add import/export tests, validate OpenSpec, then run focused backend/frontend suites.

Rollback is code-only: remove the new parser/export path and restore the old single-import response contract if needed. No schema/data migration is required.

## Open Questions

- None for v1. The user chose one import entry point, external-format export, current conflict-setting reuse, and all-or-nothing bulk behavior.
