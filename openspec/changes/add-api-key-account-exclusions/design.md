## Context

The current API-key account policy is represented by:

- `api_keys.account_assignment_scope_enabled`
- `api_key_accounts(api_key_id, account_id)`

When the flag is false, a key can use the full normal account pool. When the flag is true, the key can use only rows in `api_key_accounts`. This supports all accounts and whitelist modes, but not "all except this account."

The approved behavior is a tri-state account picker on both create and edit:

- blank: inherit the default account pool,
- tick: explicitly allow this account,
- cross: explicitly exclude this account.

If both ticks and crosses exist, routing uses allowed accounts minus excluded accounts. If the final set is empty, saving remains valid because that is an admin policy choice.

## Goals / Non-Goals

**Goals:**

- Model allowed and excluded account policy in one API-key account relation.
- Preserve existing whitelist semantics for current rows.
- Support account policy on API-key create and edit.
- Keep the dashboard UI compact with one tri-state account picker instead of separate allowlist/blacklist controls.
- Apply policy consistently to selection, preferred-account reuse, and HTTP bridge session reuse.

**Non-Goals:**

- Add a separate blacklist table.
- Prevent admins from configuring a key with no eligible accounts.
- Change global account eligibility rules such as paused, expired, unhealthy, or drained behavior.
- Add per-model or per-service-tier account policy.

## Decisions

### Use one policy relation with an assignment type

Add `assignment_type` to `api_key_accounts`, constrained to `allow` or `exclude`. Existing rows are backfilled as `allow`, which preserves today's whitelist behavior.

This keeps account policy relational, preserves foreign-key cleanup when accounts are deleted, and avoids introducing a second table with parallel lifecycle rules.

### Replace the boolean scope flag with derived semantics

The stored `account_assignment_scope_enabled` flag can stay for migration compatibility and existing response compatibility, but routing semantics should derive from the policy rows:

- any `allow` row enables whitelist behavior,
- `exclude` rows subtract from the resulting pool,
- no `allow` rows means the base pool is all normally eligible accounts.

The response can continue returning `accountAssignmentScopeEnabled` as `true` when allowed account IDs are non-empty, so existing consumers see the old meaning.

### Add explicit API fields for both lists

Dashboard API responses should return:

- `assignedAccountIds`: existing allowlist field, now allow rows only,
- `excludedAccountIds`: new exclusion field.

Create and update requests should accept both fields. Omitting a field leaves it unchanged on update. Supplying an empty list clears that side of the policy. Create accepts both lists so keys can be born with account exclusions.

### Keep tri-state UI state explicit

The React picker should own a state map of `accountId -> inherit | allow | exclude` and emit separate allow/exclude arrays. The visual states are:

- blank/dash or neutral icon: inherit,
- check icon: allow,
- x icon: exclude.

The summary label should distinguish the common cases:

- "All accounts"
- "N allowed"
- "N excluded"
- "N allowed, M excluded"

### Allow empty eligibility

The backend should not reject a policy that resolves to zero eligible accounts. A request using such a key should fail through the normal selection/no-account path, preserving admin control and avoiding special validation rules.

## Data Flow

1. Dashboard create/edit submits `assignedAccountIds` and `excludedAccountIds`.
2. API schemas validate each as a list of account IDs.
3. Service validates every referenced account exists and rejects unknown IDs.
4. Repository replaces all policy rows for the touched side or both sides in one transaction.
5. API responses map `allow` rows to `assignedAccountIds` and `exclude` rows to `excludedAccountIds`.
6. Proxy selection computes:
   - `allowed_account_ids = set(assignedAccountIds)` when non-empty, otherwise `None`,
   - `excluded_account_ids = set(excludedAccountIds)`,
   - preferred/sticky candidates are accepted only when in allowed scope and not excluded,
   - normal selection receives allowed scope and exclusion set.
7. HTTP bridge session reuse rejects a session whose account is excluded for the current API key.

## Risks / Trade-offs

- **Compatibility drift:** existing clients know only `assignedAccountIds`. Mitigation: keep that field as allow rows and keep `accountAssignmentScopeEnabled` compatible.
- **Migration mistakes:** old rows must become `allow`. Mitigation: server default plus explicit backfill in the migration.
- **Create/edit asymmetry:** current UI only has assignment editing on edit. Mitigation: reuse the same tri-state component in create and edit.
- **Selection cache leakage:** API-key policy is per request and must not be lost when routing uses cached account inputs. Mitigation: apply allowed/excluded filtering at the service selection call sites and bridge reuse guards where API key data is already present.

## Verification

- OpenSpec validation: `openspec validate add-api-key-account-exclusions --strict` and `openspec validate --specs`.
- Backend unit tests for service mapping, unknown account validation, allow/exclude replacement, and backward-compatible allowlist response mapping.
- Backend proxy tests for all four policy shapes: all, allow only, exclude only, allow minus exclude.
- Frontend tests for tri-state create/edit payloads and existing unrelated edit payload omission behavior.
- Integration flow test that creates a key with an excluded account and then edits both allow and exclude states.
