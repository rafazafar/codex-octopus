# API Key Account Exclusions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let API keys avoid selected accounts while preserving existing all-accounts and explicit-allow account routing behavior.

**Architecture:** Extend the existing `api_key_accounts` relation with an `assignment_type` value instead of adding a separate blacklist table. Backend API contracts expose allowed and excluded account IDs separately, proxy selection subtracts exclusions from the effective pool, and the dashboard uses one tri-state picker on create and edit.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, Zod, TanStack Query, pytest, Vitest, React Testing Library

---

### Task 1: Add typed API-key account policy storage

**Files:**
- Create: `app/db/alembic/versions/20260426_000000_add_api_key_account_assignment_type.py`
- Modify: `app/db/models.py`
- Modify: `app/modules/api_keys/repository.py`
- Test: `tests/unit/test_api_keys_service.py`

- [ ] **Step 1: Write the failing service/repository fake expectations**

Update the fake repository in `tests/unit/test_api_keys_service.py` so account assignment rows can carry `assignment_type`. This should fail before the model field exists.

```python
# tests/unit/test_api_keys_service.py
async def replace_account_assignments(
    self,
    key_id: str,
    account_ids: list[str],
    *,
    assignment_type: str = "allow",
    commit: bool = True,
) -> None:
    del commit
    assignments = [
        ApiKeyAccountAssignment(
            api_key_id=key_id,
            account_id=account_id,
            assignment_type=assignment_type,
        )
        for account_id in account_ids
    ]
    existing = [
        assignment
        for assignment in self._account_assignments.get(key_id, [])
        if assignment.assignment_type != assignment_type
    ]
    self._account_assignments[key_id] = existing + assignments
    row = self.rows.get(key_id)
    if row is not None:
        row.account_assignments = self._account_assignments[key_id]
```

- [ ] **Step 2: Run the focused test file to verify the missing model field**

Run: `uv run python -m pytest tests/unit/test_api_keys_service.py -k account -q`

Expected: FAIL with an error showing `assignment_type` is not accepted or not present on `ApiKeyAccountAssignment`.

- [ ] **Step 3: Add the ORM field**

```python
# app/db/models.py
class ApiKeyAccountAssignment(Base):
    __tablename__ = "api_key_accounts"

    api_key_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        primary_key=True,
    )
    account_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assignment_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="allow",
        server_default="allow",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
```

Keep the primary key as `(api_key_id, account_id)`. The service will reject attempts to store the same account in both allow and exclude policy lists; no duplicate row is needed.

- [ ] **Step 4: Add the Alembic migration**

```python
# app/db/alembic/versions/20260426_000000_add_api_key_account_assignment_type.py
"""add api key account assignment type

Revision ID: 20260426_000000_add_api_key_account_assignment_type
Revises: 20260419_020000_add_automation_run_cycles_snapshot_tables
Create Date: 2026-04-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260426_000000_add_api_key_account_assignment_type"
down_revision = "20260419_020000_add_automation_run_cycles_snapshot_tables"
branch_labels = None
depends_on = None


def _columns(bind: sa.engine.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "api_key_accounts")
    if "assignment_type" not in columns:
        with op.batch_alter_table("api_key_accounts") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "assignment_type",
                    sa.String(length=16),
                    nullable=False,
                    server_default="allow",
                )
            )
    op.execute(
        sa.text(
            "UPDATE api_key_accounts "
            "SET assignment_type = 'allow' "
            "WHERE assignment_type IS NULL OR assignment_type = ''"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "api_key_accounts")
    if "assignment_type" in columns:
        with op.batch_alter_table("api_key_accounts") as batch_op:
            batch_op.drop_column("assignment_type")
```

Before implementing, confirm the current Alembic head with `uv run codex-lb-db heads` or the repo's existing migration check command. If `20260419_020000_add_automation_run_cycles_snapshot_tables` is no longer the sole current head, set `down_revision` to the actual current head and add a merge revision if needed.

- [ ] **Step 5: Update repository replacement by assignment type**

```python
# app/modules/api_keys/repository.py
async def replace_account_assignments(
    self,
    key_id: str,
    account_ids: list[str],
    *,
    assignment_type: str = "allow",
    commit: bool = True,
) -> None:
    await self._session.execute(
        delete(ApiKeyAccountAssignment).where(
            ApiKeyAccountAssignment.api_key_id == key_id,
            ApiKeyAccountAssignment.assignment_type == assignment_type,
        )
    )
    for account_id in account_ids:
        self._session.add(
            ApiKeyAccountAssignment(
                api_key_id=key_id,
                account_id=account_id,
                assignment_type=assignment_type,
            )
        )
    if commit:
        await self._session.commit()
        parent = await self.get_by_id(key_id)
        if parent is not None:
            await self._session.refresh(parent, attribute_names=["account_assignments"])
```

- [ ] **Step 6: Run storage-focused tests**

Run: `uv run python -m pytest tests/unit/test_api_keys_service.py -k account -q`

Expected: existing account-assignment tests pass after later service changes; at this point failures about missing service fields are expected and addressed in Task 2.

### Task 2: Add backend CRUD contract for excluded accounts

**Files:**
- Modify: `app/modules/api_keys/schemas.py`
- Modify: `app/modules/api_keys/api.py`
- Modify: `app/modules/api_keys/service.py`
- Modify: `tests/unit/test_api_keys_service.py`
- Modify: `tests/integration/test_api_keys_api.py`

- [ ] **Step 1: Add failing service tests for exclusion policy**

Append tests near the existing assignment-scope test in `tests/unit/test_api_keys_service.py`.

```python
@pytest.mark.asyncio
async def test_update_key_stores_excluded_accounts_without_enabling_allow_scope() -> None:
    repo = _FakeApiKeysRepository()
    service = ApiKeysService(repo)
    repo._accounts = {
        "acc-a": Account(id="acc-a", email="a@example.com", plan_type="plus", access_token_encrypted=b"a", refresh_token_encrypted=b"r", id_token_encrypted=b"i", last_refresh=utcnow(), status=AccountStatus.ACTIVE),
    }
    created = await service.create_key(ApiKeyCreateData(name="exclude-only", allowed_models=None, expires_at=None))

    updated = await service.update_key(
        created.id,
        ApiKeyUpdateData(excluded_account_ids=["acc-a"], excluded_account_ids_set=True),
    )

    assert updated.account_assignment_scope_enabled is False
    assert updated.assigned_account_ids == []
    assert updated.excluded_account_ids == ["acc-a"]


@pytest.mark.asyncio
async def test_update_key_rejects_same_account_allowed_and_excluded() -> None:
    repo = _FakeApiKeysRepository()
    service = ApiKeysService(repo)
    repo._accounts = {
        "acc-a": Account(id="acc-a", email="a@example.com", plan_type="plus", access_token_encrypted=b"a", refresh_token_encrypted=b"r", id_token_encrypted=b"i", last_refresh=utcnow(), status=AccountStatus.ACTIVE),
    }
    created = await service.create_key(ApiKeyCreateData(name="overlap", allowed_models=None, expires_at=None))

    with pytest.raises(ValueError, match="cannot be both allowed and excluded"):
        await service.update_key(
            created.id,
            ApiKeyUpdateData(
                assigned_account_ids=["acc-a"],
                assigned_account_ids_set=True,
                excluded_account_ids=["acc-a"],
                excluded_account_ids_set=True,
            ),
        )
```

- [ ] **Step 2: Add request/response schema fields**

```python
# app/modules/api_keys/schemas.py
class ApiKeyCreateRequest(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    allowed_models: list[str] | None = None
    enforced_model: str | None = Field(default=None, min_length=1)
    enforced_reasoning_effort: str | None = Field(default=None, pattern=r"(?i)^(none|minimal|low|medium|high|xhigh)$")
    enforced_service_tier: str | None = Field(default=None, pattern=r"(?i)^(auto|default|priority|flex|fast)$")
    weekly_token_limit: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    assigned_account_ids: list[str] | None = None
    excluded_account_ids: list[str] | None = None
    limits: list[LimitRuleCreate] | None = None


class ApiKeyUpdateRequest(DashboardModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    allowed_models: list[str] | None = None
    enforced_model: str | None = Field(default=None, min_length=1)
    enforced_reasoning_effort: str | None = Field(default=None, pattern=r"(?i)^(none|minimal|low|medium|high|xhigh)$")
    enforced_service_tier: str | None = Field(default=None, pattern=r"(?i)^(auto|default|priority|flex|fast)$")
    weekly_token_limit: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None
    is_active: bool | None = None
    assigned_account_ids: list[str] | None = None
    excluded_account_ids: list[str] | None = None
    limits: list[LimitRuleCreate] | None = None
    reset_usage: bool | None = None


class ApiKeyResponse(DashboardModel):
    ...
    account_assignment_scope_enabled: bool = False
    assigned_account_ids: list[str] = Field(default_factory=list)
    excluded_account_ids: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Extend service dataclasses and mapper**

```python
# app/modules/api_keys/service.py
@dataclass(frozen=True, slots=True)
class ApiKeyCreateData:
    ...
    assigned_account_ids: list[str] | None = None
    excluded_account_ids: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ApiKeyUpdateData:
    ...
    excluded_account_ids: list[str] | None = None
    excluded_account_ids_set: bool = False


@dataclass(frozen=True, slots=True)
class ApiKeyData:
    ...
    account_assignment_scope_enabled: bool = False
    assigned_account_ids: list[str] = field(default_factory=list)
    excluded_account_ids: list[str] = field(default_factory=list)
```

```python
def _split_account_assignments(assignments: list[ApiKeyAccountAssignment]) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    excluded: list[str] = []
    for assignment in assignments:
        if assignment.assignment_type == "exclude":
            excluded.append(assignment.account_id)
        else:
            allowed.append(assignment.account_id)
    return allowed, excluded


def _to_api_key_data(row: ApiKey, *, usage_summary: ApiKeyUsageSummaryData | None = None) -> ApiKeyData:
    limits = [_to_limit_rule_data(limit) for limit in row.limits] if row.limits else []
    account_assignments = list(getattr(row, "account_assignments", []))
    assigned_account_ids, excluded_account_ids = _split_account_assignments(account_assignments)
    return ApiKeyData(
        ...
        account_assignment_scope_enabled=bool(assigned_account_ids),
        assigned_account_ids=assigned_account_ids,
        excluded_account_ids=excluded_account_ids,
    )
```

- [ ] **Step 4: Validate account policy in the service**

```python
def _normalize_account_ids(account_ids: list[str] | None) -> list[str]:
    if not account_ids:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for account_id in account_ids:
        stripped = account_id.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        normalized.append(stripped)
    return normalized


async def _validate_account_ids_exist(
    self,
    account_ids: list[str],
) -> None:
    existing_accounts = await self._repository.list_accounts_by_ids(account_ids)
    existing_account_ids = {account.id for account in existing_accounts}
    missing_account_ids = [account_id for account_id in account_ids if account_id not in existing_account_ids]
    if missing_account_ids:
        missing = ", ".join(missing_account_ids)
        raise ValueError(f"Unknown account ids: {missing}")
```

In `update_key`, compute effective allowed/excluded IDs using the submitted field when set, otherwise the existing row's current policy. Reject overlap with:

```python
overlap = sorted(set(effective_assigned_account_ids) & set(effective_excluded_account_ids))
if overlap:
    joined = ", ".join(overlap)
    raise ValueError(f"Accounts cannot be both allowed and excluded: {joined}")
```

Set `account_assignment_scope_enabled=bool(effective_assigned_account_ids)` when either account policy side changes.

- [ ] **Step 5: Persist create-time account policy**

In `create_key`, after creating the row and before returning, validate and persist both policy lists in the same transaction path used for limits. The minimal pattern:

```python
assigned_account_ids = _normalize_account_ids(payload.assigned_account_ids)
excluded_account_ids = _normalize_account_ids(payload.excluded_account_ids)
overlap = sorted(set(assigned_account_ids) & set(excluded_account_ids))
if overlap:
    raise ValueError(f"Accounts cannot be both allowed and excluded: {', '.join(overlap)}")
await self._validate_account_ids_exist([*assigned_account_ids, *excluded_account_ids])
created.account_assignment_scope_enabled = bool(assigned_account_ids)
...
await self._repository.replace_account_assignments(created.id, assigned_account_ids, assignment_type="allow", commit=False)
await self._repository.replace_account_assignments(created.id, excluded_account_ids, assignment_type="exclude", commit=False)
await self._repository.commit()
created = await self._repository.get_by_id(created.id)
```

- [ ] **Step 6: Wire API request/response mapping**

```python
# app/modules/api_keys/api.py
def _to_response(row: ApiKeyData) -> ApiKeyResponse:
    return ApiKeyResponse(
        ...
        account_assignment_scope_enabled=row.account_assignment_scope_enabled,
        assigned_account_ids=row.assigned_account_ids,
        excluded_account_ids=row.excluded_account_ids,
        ...
    )
```

In `create_api_key`, pass the two new payload fields into `ApiKeyCreateData`. In `update_api_key`, pass:

```python
excluded_account_ids=payload.excluded_account_ids,
excluded_account_ids_set="excluded_account_ids" in fields,
```

- [ ] **Step 7: Add API integration coverage**

Add a test in `tests/integration/test_api_keys_api.py` that creates a key with `excludedAccountIds`, reads it back, and verifies `assignedAccountIds: []`, `excludedAccountIds`, and `accountAssignmentScopeEnabled: false`.

Run: `uv run python -m pytest tests/unit/test_api_keys_service.py tests/integration/test_api_keys_api.py -k "account or excluded" -q`

Expected: PASS.

### Task 3: Enforce exclusions in proxy selection and bridge reuse

**Files:**
- Modify: `app/modules/proxy/service.py`
- Modify: `tests/unit/test_proxy_http_bridge.py`
- Modify: `tests/integration/test_http_responses_bridge.py`

- [ ] **Step 1: Add failing proxy policy tests**

In `tests/unit/test_proxy_http_bridge.py`, add a test near existing account-assignment-scope tests:

```python
def test_http_bridge_session_rejects_excluded_account() -> None:
    session = _make_http_bridge_session(account_id="acc-a")
    api_key = _make_api_key_data(
        assigned_account_ids=[],
        excluded_account_ids=["acc-a"],
        account_assignment_scope_enabled=False,
    )

    assert _http_bridge_session_allows_api_key(session, api_key) is False
```

In `tests/integration/test_http_responses_bridge.py`, add or extend selection tests so an API key excluding `acc-a` selects `acc-b` when both accounts are otherwise eligible.

- [ ] **Step 2: Add helpers in proxy service**

```python
# app/modules/proxy/service.py
def _api_key_allowed_account_ids(api_key: ApiKeyData | None) -> set[str] | None:
    if api_key is None:
        return None
    assigned = set(api_key.assigned_account_ids)
    return assigned if assigned else None


def _api_key_excluded_account_ids(api_key: ApiKeyData | None) -> set[str]:
    if api_key is None:
        return set()
    return set(api_key.excluded_account_ids)


def _api_key_allows_account(api_key: ApiKeyData | None, account_id: str) -> bool:
    allowed = _api_key_allowed_account_ids(api_key)
    excluded = _api_key_excluded_account_ids(api_key)
    if account_id in excluded:
        return False
    return allowed is None or account_id in allowed
```

- [ ] **Step 3: Apply helpers in `_select_account_with_budget`**

Replace current scoped account logic:

```python
scoped_account_ids = _api_key_allowed_account_ids(api_key)
api_key_excluded_account_ids = _api_key_excluded_account_ids(api_key)
excluded_account_ids_set = set(exclude_account_ids or ()) | api_key_excluded_account_ids
```

Replace the preferred-account guard with:

```python
if (
    preferred_account_id is not None
    and preferred_account_id not in excluded_account_ids_set
    and _api_key_allows_account(api_key, preferred_account_id)
):
```

Ensure the normal `select_account` call receives:

```python
account_ids=scoped_account_ids,
exclude_account_ids=excluded_account_ids_set,
```

Use the actual parameter names in the existing nearby call sites; do not add a new load-balancer API if the current method already accepts exclusions.

- [ ] **Step 4: Apply helpers to bridge reuse**

```python
def _http_bridge_session_allows_api_key(session: "_HTTPBridgeSession", api_key: ApiKeyData | None) -> bool:
    return _api_key_allows_account(api_key, session.account.id)
```

Search for direct checks of `api_key.account_assignment_scope_enabled` in `app/modules/proxy/service.py` and replace them with `_api_key_allows_account` or the allowed/excluded helper pair.

- [ ] **Step 5: Run proxy tests**

Run: `uv run python -m pytest tests/unit/test_proxy_http_bridge.py -k "assignment or excluded or bridge_session" -q`

Run: `uv run python -m pytest tests/integration/test_http_responses_bridge.py -k "assignment or excluded" -q`

Expected: PASS.

### Task 4: Build the tri-state frontend account policy picker

**Files:**
- Rename/replace: `frontend/src/features/api-keys/components/account-multi-select.tsx`
- Modify: `frontend/src/features/api-keys/components/api-key-create-dialog.tsx`
- Modify: `frontend/src/features/api-keys/components/api-key-edit-dialog.tsx`
- Modify: `frontend/src/features/api-keys/schemas.ts`
- Modify: `frontend/src/test/mocks/factories.ts`
- Modify: `frontend/src/features/api-keys/components/api-key-edit-dialog.test.tsx`
- Modify: `frontend/src/__integration__/api-keys-flow.test.tsx`

- [ ] **Step 1: Update frontend schemas and factories**

```ts
// frontend/src/features/api-keys/schemas.ts
export const ApiKeySchema = z.object({
  ...
  accountAssignmentScopeEnabled: z.boolean().default(false),
  assignedAccountIds: z.array(z.string()).default([]),
  excludedAccountIds: z.array(z.string()).default([]),
  ...
});

export const ApiKeyCreateRequestSchema = z.object({
  ...
  assignedAccountIds: z.array(z.string()).optional(),
  excludedAccountIds: z.array(z.string()).optional(),
  limits: z.array(LimitRuleCreateSchema).optional(),
});

export const ApiKeyUpdateRequestSchema = z.object({
  ...
  assignedAccountIds: z.array(z.string()).optional(),
  excludedAccountIds: z.array(z.string()).optional(),
  limits: z.array(LimitRuleCreateSchema).optional(),
  resetUsage: z.boolean().optional(),
});
```

Update `createApiKey` in `frontend/src/test/mocks/factories.ts` so mocked keys default `excludedAccountIds: []` and allow overrides.

- [ ] **Step 2: Replace the picker contract**

```ts
// frontend/src/features/api-keys/components/account-multi-select.tsx
export type AccountPolicyValue = {
  allowedAccountIds: string[];
  excludedAccountIds: string[];
};

export type AccountMultiSelectProps = {
  value: AccountPolicyValue;
  onChange: (value: AccountPolicyValue) => void;
  placeholder?: string;
  triggerId?: string;
  ariaInvalid?: boolean;
  ariaDescribedBy?: string;
  triggerClassName?: string;
};

type AccountPolicyState = "inherit" | "allow" | "exclude";
```

Compute state per account:

```ts
function getAccountState(value: AccountPolicyValue, accountId: string): AccountPolicyState {
  if (value.excludedAccountIds.includes(accountId)) return "exclude";
  if (value.allowedAccountIds.includes(accountId)) return "allow";
  return "inherit";
}

function nextAccountState(state: AccountPolicyState): AccountPolicyState {
  if (state === "inherit") return "allow";
  if (state === "allow") return "exclude";
  return "inherit";
}
```

On row click, remove the account from both arrays, then add it to the target array when target is `allow` or `exclude`.

- [ ] **Step 3: Render tri-state rows**

Use lucide icons already available in the project:

```tsx
import { Check, ChevronsUpDown, Minus, X } from "lucide-react";
```

For each account row, render a stable icon slot:

```tsx
const state = getAccountState(value, account.accountId);
const Icon = state === "allow" ? Check : state === "exclude" ? X : Minus;

<DropdownMenuCheckboxItem
  key={account.accountId}
  checked={state !== "inherit"}
  onCheckedChange={() => cycle(account.accountId)}
  onSelect={(event) => event.preventDefault()}
>
  <span className="mr-2 flex size-4 items-center justify-center">
    <Icon className={cn("size-3", state === "exclude" ? "text-destructive" : "")} />
  </span>
  {account.email}
</DropdownMenuCheckboxItem>
```

Keep badges below the trigger, rendering allowed badges as secondary and excluded badges with a destructive/outline treatment if the local design tokens support it. Each badge remove action returns that account to inherit.

- [ ] **Step 4: Add create-dialog policy state**

```tsx
// frontend/src/features/api-keys/components/api-key-create-dialog.tsx
const [accountPolicy, setAccountPolicy] = useState<AccountPolicyValue>({
  allowedAccountIds: [],
  excludedAccountIds: [],
});
```

Add the picker under allowed models:

```tsx
<div className="space-y-1">
  <label className="text-sm font-medium">Account policy</label>
  <AccountMultiSelect value={accountPolicy} onChange={setAccountPolicy} />
</div>
```

Submit both lists only when non-empty:

```ts
assignedAccountIds: accountPolicy.allowedAccountIds.length > 0 ? accountPolicy.allowedAccountIds : undefined,
excludedAccountIds: accountPolicy.excludedAccountIds.length > 0 ? accountPolicy.excludedAccountIds : undefined,
```

Reset `accountPolicy` after successful create.

- [ ] **Step 5: Update edit-dialog dirty tracking**

Initialize:

```tsx
const [accountPolicy, setAccountPolicy] = useState<AccountPolicyValue>({
  allowedAccountIds: apiKey.assignedAccountIds,
  excludedAccountIds: apiKey.excludedAccountIds,
});
```

Replace `hasSelectionChange` with:

```ts
function hasIdListChange(initialIds: string[], nextIds: string[]): boolean {
  if (initialIds.length !== nextIds.length) return true;
  const initialIdSet = new Set(initialIds);
  return nextIds.some((accountId) => !initialIdSet.has(accountId));
}

function hasAccountPolicyChange(apiKey: ApiKey, next: AccountPolicyValue): boolean {
  return (
    hasIdListChange(apiKey.assignedAccountIds, next.allowedAccountIds) ||
    hasIdListChange(apiKey.excludedAccountIds, next.excludedAccountIds)
  );
}
```

On submit:

```ts
if (hasAccountPolicyChange(apiKey, accountPolicy)) {
  payload.assignedAccountIds = accountPolicy.allowedAccountIds;
  payload.excludedAccountIds = accountPolicy.excludedAccountIds;
}
```

- [ ] **Step 6: Add frontend tests**

In `api-key-edit-dialog.test.tsx`, update existing account tests to the new labels and add:

```ts
it("submits excluded accounts when account policy changes", async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  renderWithProviders(
    <ApiKeyEditDialog open busy={false} apiKey={createApiKey()} onOpenChange={vi.fn()} onSubmit={onSubmit} />,
  );

  await user.click(await screen.findByRole("button", { name: "All accounts" }));
  await user.click(screen.getByRole("menuitemcheckbox", { name: "primary@example.com" }));
  await user.click(screen.getByRole("menuitemcheckbox", { name: "primary@example.com" }));
  await user.keyboard("{Escape}");
  await user.click(screen.getByRole("button", { name: "Save" }));

  await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
  expect(onSubmit.mock.calls[0][0].assignedAccountIds).toEqual([]);
  expect(onSubmit.mock.calls[0][0].excludedAccountIds).toEqual(["acc_primary"]);
});
```

Add create-flow integration coverage that opens the create dialog, excludes one account, submits, and asserts the mocked API receives `excludedAccountIds`.

- [ ] **Step 7: Run frontend tests**

Run: `cd frontend && npm test -- --run src/features/api-keys/components/api-key-edit-dialog.test.tsx src/__integration__/api-keys-flow.test.tsx`

Expected: PASS.

### Task 5: Validate specs and focused suites

**Files:**
- Modify: `openspec/changes/add-api-key-account-exclusions/tasks.md`

- [ ] **Step 1: Validate OpenSpec change**

Run: `openspec validate add-api-key-account-exclusions --strict`

Expected: PASS.

Run: `openspec validate --specs`

Expected: PASS.

- [ ] **Step 2: Run backend focused suites**

Run: `uv run python -m pytest tests/unit/test_api_keys_service.py tests/unit/test_proxy_http_bridge.py -k "account or excluded or assignment" -q`

Expected: PASS.

Run: `uv run python -m pytest tests/integration/test_api_keys_api.py tests/integration/test_http_responses_bridge.py -k "account or excluded or assignment" -q`

Expected: PASS.

- [ ] **Step 3: Run frontend focused suites**

Run: `cd frontend && npm test -- --run src/features/api-keys/components/api-key-edit-dialog.test.tsx src/__integration__/api-keys-flow.test.tsx`

Expected: PASS.

- [ ] **Step 4: Mark OpenSpec tasks complete**

After implementation and verification pass, update `openspec/changes/add-api-key-account-exclusions/tasks.md` so completed items use `[x]`.
