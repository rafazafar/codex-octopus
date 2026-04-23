## Context

The Accounts dashboard currently stores lifecycle state (`status`) and token metadata, but it has no independent concept of an operator-managed account expiry date. The user wants expiry to behave as a soft lease:

- accounts default to expiring 30 days after add/import,
- portable imports preserve expiry when the payload provides it,
- re-imports that do not include expiry reset the lease to 30 days,
- expired accounts are excluded from selection/routing,
- expired accounts remain visible in `/accounts`,
- operators can manually edit expiry from the Accounts UI.

This needs to stay distinct from `paused` or `deactivated`, because expiry is reversible and should not erase the underlying lifecycle reason an account is otherwise in.

## Goals / Non-Goals

**Goals:**

- Introduce a dedicated account expiry field and round-trip it through dashboard APIs.
- Make expiry portable when importing/exporting the shared account JSON format.
- Apply a 30-day default whenever an add/import path does not provide expiry.
- Exclude expired accounts from normal routing/selection without overwriting `status`.
- Add an explicit manual expiry edit flow in the Accounts UI.

**Non-Goals:**

- Auto-deleting expired accounts.
- Reusing `deactivated` as the expiry state.
- Building a broader account-renewal workflow beyond setting or clearing the expiry date.

## Decisions

### Use a dedicated `expires_at` field on accounts

Account expiry is separate from lifecycle status, so it should be modeled as its own nullable datetime field on `accounts`.

- `status` continues to represent lifecycle state such as `active`, `paused`, or `deactivated`.
- `expires_at` represents operator-managed lease end.
- API responses expose both `expiresAt` and a derived `isExpired` flag so the frontend can render the state without owning the enforcement logic.

**Alternative considered:** repurpose `status` or `deactivation_reason`. Rejected because expiry is intentionally reversible and should not be conflated with stronger lifecycle states.

### Default expiry at ingestion boundaries

All add/import paths should assign expiry at the moment the account record is written.

- New account from OAuth/import with no incoming expiry: `now + 30 days`.
- Portable import with incoming expiry: preserve the payload value.
- Re-import/update with no incoming expiry: reset to `now + 30 days`, per the approved behavior.

This keeps defaulting centralized in the backend and avoids UI- or format-specific exceptions.

### Make expiry round-trip through the portable format

The portable account model should gain an explicit expiry field so exported accounts can preserve operator intent when moved between tools. `auth.json` remains supported as-is; when that format lacks expiry, the backend applies the default lease.

**Alternative considered:** keep expiry local-only. Rejected because re-import behavior would become lossy and the user explicitly wants payload-provided expiry to win when present.

### Soft-enforce expiry in account selection, not by status mutation

Expired accounts should be treated as ineligible for normal routing/selection, but the system should not rewrite their stored `status`. Operators still need to see the account in `/accounts`, understand why it is excluded, and extend or clear the expiry.

This means selection code should consult effective expiry when filtering eligible accounts, while dashboard list/detail endpoints continue returning the record.

### Add a focused expiry update endpoint

Manual editing should use a narrow endpoint such as `PATCH /api/accounts/{account_id}/expiry` with a nullable `expires_at` payload.

That keeps expiry changes separate from pause/resume semantics and lets tests target one clear contract:

- set a new expiry,
- extend an expiry,
- clear expiry,
- reject invalid timestamps,
- return not found for missing accounts.

## Data Flow

1. OAuth add/import normalizes incoming account data.
2. The accounts service resolves the effective expiry:
   - portable payload expiry when present,
   - otherwise `utcnow() + 30 days`.
3. The repository persists `expires_at` with the rest of the account row.
4. List/detail mappers return `expiresAt` plus derived `isExpired`.
5. Selection/routing paths exclude accounts whose `expires_at <= now`.
6. Manual expiry edits update only the expiry field and refresh account-related queries.

## Risks / Trade-offs

- **Selection regressions:** filtering expired accounts in the wrong layer could leave some routing paths unaware of expiry. Mitigation: enforce in the shared account-selection path rather than only in dashboard presentation.
- **Timezone drift:** clients may submit timezone-aware values while the backend stores naive UTC datetimes. Mitigation: normalize on write and compute `isExpired` server-side.
- **Portable-format drift:** adding expiry to the external JSON shape changes interoperability expectations. Mitigation: make import tolerant and export explicit/stable.
- **Operator confusion with status:** an expired account might still show `active`. Mitigation: surface expiry state clearly in list/detail UI and treat expiry as a separate label from status.

## Migration Plan

1. Add OpenSpec artifacts for the `account-expiry` capability.
2. Add a schema migration for `accounts.expires_at`.
3. Thread expiry through account persistence, import/export normalization, and account summaries.
4. Enforce expiry in account selection/routing paths.
5. Add the dedicated expiry update API and dashboard editing UI.
6. Validate OpenSpec and run focused backend/frontend tests.

Rollback is code-and-schema based: remove enforcement and UI usage, then drop or ignore `expires_at` in a follow-up migration if necessary.
