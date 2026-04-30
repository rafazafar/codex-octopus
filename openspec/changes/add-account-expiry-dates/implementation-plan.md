# Account Expiry Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add account-level expiry dates that default to 30 days on add/import, round-trip through portable import/export, exclude expired accounts from normal routing, and remain editable from the Accounts UI.

**Architecture:** Add a nullable `expires_at` field to the `accounts` table, thread it through account persistence and API summaries, and treat expiry as a separate eligibility constraint rather than a lifecycle `status`. Keep expiry enforcement centralized in backend selection/filter helpers and expose `expiresAt` plus `isExpired` to the frontend for rendering and edit flows.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TanStack Query, Zod, Vitest, pytest

---

### Task 1: Add expiry storage and repository support

**Files:**
- Create: `app/db/alembic/versions/20260424_000000_add_accounts_expires_at.py`
- Modify: `app/db/models.py`
- Modify: `app/modules/accounts/repository.py`
- Test: `tests/integration/test_migrations.py`
- Test: `tests/integration/test_db_models.py`

- [ ] **Step 1: Write the failing migration/model tests**

```python
# tests/integration/test_db_models.py
@pytest.mark.asyncio
async def test_account_model_persists_nullable_expires_at(db_setup):
    async with SessionLocal() as session:
        account = _make_account("acc-expiry", "expiry@example.com")
        account.expires_at = datetime(2026, 5, 24, 0, 0, 0)
        session.add(account)
        await session.commit()

        stored = await session.get(Account, "acc-expiry")
        assert stored is not None
        assert stored.expires_at == datetime(2026, 5, 24, 0, 0, 0)
```

```python
# tests/integration/test_migrations.py
def test_upgrade_adds_accounts_expires_at_column(sqlite_engine):
    inspector = inspect(sqlite_engine)
    columns = {column["name"] for column in inspector.get_columns("accounts")}
    assert "expires_at" in columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_db_models.py -k expires_at -v`
Expected: FAIL because `Account` has no `expires_at` field yet.

Run: `pytest tests/integration/test_migrations.py -k expires_at -v`
Expected: FAIL because the migration/column does not exist yet.

- [ ] **Step 3: Add the model column and migration**

```python
# app/db/models.py
class Account(Base):
    __tablename__ = "accounts"
    ...
    last_refresh: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

```python
# app/db/alembic/versions/20260424_000000_add_accounts_expires_at.py
from alembic import op
import sqlalchemy as sa

revision = "20260424_000000"
down_revision = "20260419_020000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "expires_at")
```

- [ ] **Step 4: Add repository update support**

```python
# app/modules/accounts/repository.py
    async def update_expiry(self, account_id: str, expires_at: datetime | None) -> bool:
        result = await self._session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(expires_at=expires_at)
            .returning(Account.id)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/integration/test_db_models.py -k expires_at -v`
Expected: PASS

Run: `pytest tests/integration/test_migrations.py -k expires_at -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/db/models.py app/db/alembic/versions/20260424_000000_add_accounts_expires_at.py app/modules/accounts/repository.py tests/integration/test_db_models.py tests/integration/test_migrations.py
git commit -m "feat(accounts): add account expiry storage"
```

### Task 2: Thread expiry through account schemas, import/export, and manual update API

**Files:**
- Modify: `app/modules/accounts/schemas.py`
- Modify: `app/modules/accounts/mappers.py`
- Modify: `app/modules/accounts/portable.py`
- Modify: `app/modules/accounts/service.py`
- Modify: `app/modules/accounts/api.py`
- Test: `tests/integration/test_accounts_api.py`
- Test: `tests/integration/test_accounts_api_extended.py`

- [ ] **Step 1: Write the failing API/import tests**

```python
# tests/integration/test_accounts_api.py
@pytest.mark.asyncio
async def test_import_defaults_expiry_to_30_days(async_client):
    auth_json = _make_auth_json("acc_expiry_default", "default-expiry@example.com")
    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(auth_json), "application/json")},
    )

    assert response.status_code == 200
    account = next(item for item in (await async_client.get("/api/accounts")).json()["accounts"] if item["email"] == "default-expiry@example.com")
    assert account["expiresAt"] is not None
    assert account["isExpired"] is False
```

```python
# tests/integration/test_accounts_api_extended.py
@pytest.mark.asyncio
async def test_portable_import_preserves_expiry(async_client):
    portable_payload = [_make_portable_account_record("acc_portable_expiry", "portable-expiry@example.com")]
    portable_payload[0]["expires_at"] = 1_780_617_600

    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("portable.json", json.dumps(portable_payload), "application/json")},
    )

    assert response.status_code == 200
    account = next(item for item in (await async_client.get("/api/accounts")).json()["accounts"] if item["email"] == "portable-expiry@example.com")
    assert account["expiresAt"] == _iso_utc(1_780_617_600)
```

```python
# tests/integration/test_accounts_api_extended.py
@pytest.mark.asyncio
async def test_patch_account_expiry_sets_and_clears_value(async_client):
    await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(_make_auth_json("acc_patch_expiry", "patch-expiry@example.com")), "application/json")},
    )

    set_response = await async_client.patch(
        "/api/accounts/acc_patch_expiry/expiry",
        json={"expiresAt": "2026-06-01T00:00:00Z"},
    )
    assert set_response.status_code == 200
    assert set_response.json()["expiresAt"] == "2026-06-01T00:00:00+00:00"

    clear_response = await async_client.patch(
        "/api/accounts/acc_patch_expiry/expiry",
        json={"expiresAt": None},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["expiresAt"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_accounts_api.py -k expiry -v`
Expected: FAIL because account summaries do not include `expiresAt` or `isExpired`.

Run: `pytest tests/integration/test_accounts_api_extended.py -k expiry -v`
Expected: FAIL because the portable format and patch endpoint do not support expiry yet.

- [ ] **Step 3: Extend schemas and mappers**

```python
# app/modules/accounts/schemas.py
class AccountSummary(DashboardModel):
    ...
    expires_at: datetime | None = None
    is_expired: bool = False


class AccountExpiryUpdateRequest(DashboardModel):
    expires_at: datetime | None = None


class AccountExpiryUpdateResponse(DashboardModel):
    account_id: str
    expires_at: datetime | None = None
    is_expired: bool
```

```python
# app/modules/accounts/mappers.py
def _account_to_summary(...):
    ...
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = account.expires_at
    is_expired = expires_at is not None and expires_at <= now
    return AccountSummary(
        ...
        expires_at=expires_at,
        is_expired=is_expired,
    )
```

- [ ] **Step 4: Add expiry normalization to portable parsing and persistence**

```python
# app/modules/accounts/portable.py
class PortableAccountRecord(BaseModel):
    ...
    expires_at: datetime | None = None


class PortableExternalAccountImport(BaseModel):
    ...
    expires_at: int | None = None


class PortableExternalAccountExport(BaseModel):
    ...
    expires_at: int | None = None
```

```python
# app/modules/accounts/service.py
_DEFAULT_ACCOUNT_EXPIRY_DAYS = 30


def _resolve_account_expiry(
    *,
    imported_expires_at: datetime | None,
    now: datetime,
) -> datetime:
    if imported_expires_at is not None:
        return imported_expires_at
    return now + timedelta(days=_DEFAULT_ACCOUNT_EXPIRY_DAYS)
```

```python
# app/modules/accounts/service.py
                now = utcnow()
                account = Account(
                    ...
                    expires_at=_resolve_account_expiry(
                        imported_expires_at=portable_account.expires_at,
                        now=now,
                    ),
                )
```

- [ ] **Step 5: Add the expiry patch API**

```python
# app/modules/accounts/api.py
@router.patch("/{account_id}/expiry", response_model=AccountExpiryUpdateResponse)
async def update_account_expiry(
    account_id: str,
    payload: AccountExpiryUpdateRequest,
    context: AccountsContext = Depends(get_accounts_context),
) -> AccountExpiryUpdateResponse:
    result = await context.service.update_account_expiry(account_id, payload.expires_at)
    if result is None:
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return result
```

```python
# app/modules/accounts/service.py
async def update_account_expiry(self, account_id: str, expires_at: datetime | None) -> AccountExpiryUpdateResponse | None:
    normalized = _to_utc_naive(expires_at)
    updated = await self._repo.update_expiry(account_id, normalized)
    if not updated:
        return None
    account = await self._repo.get_by_id(account_id)
    assert account is not None
    summary = _account_to_summary(account, None, None, None, None, self._encryptor)
    return AccountExpiryUpdateResponse(
        account_id=account.id,
        expires_at=summary.expires_at,
        is_expired=summary.is_expired,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/integration/test_accounts_api.py -k expiry -v`
Expected: PASS

Run: `pytest tests/integration/test_accounts_api_extended.py -k expiry -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add app/modules/accounts/schemas.py app/modules/accounts/mappers.py app/modules/accounts/portable.py app/modules/accounts/service.py app/modules/accounts/api.py tests/integration/test_accounts_api.py tests/integration/test_accounts_api_extended.py
git commit -m "feat(accounts): add expiry api and import rules"
```

### Task 3: Enforce expiry in account selection and proxy-facing eligibility

**Files:**
- Modify: `app/modules/proxy/helpers.py`
- Modify: `app/modules/proxy/api.py`
- Modify: `app/modules/proxy/load_balancer.py`
- Modify: `app/core/openai/model_refresh_scheduler.py`
- Test: `tests/integration/test_load_balancer_integration.py`
- Test: `tests/integration/test_proxy_api_extended.py`

- [ ] **Step 1: Write the failing routing tests**

```python
# tests/integration/test_load_balancer_integration.py
@pytest.mark.asyncio
async def test_load_balancer_skips_expired_active_account(db_setup):
    encryptor = TokenEncryptor()
    now = utcnow()
    expired = now - timedelta(minutes=1)
    fresh = now + timedelta(days=7)

    expired_account = Account(
        id="acc_expired",
        email="expired@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access-a"),
        refresh_token_encrypted=encryptor.encrypt("refresh-a"),
        id_token_encrypted=encryptor.encrypt("id-a"),
        last_refresh=now,
        expires_at=expired,
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )
    fresh_account = Account(
        id="acc_fresh",
        email="fresh@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access-b"),
        refresh_token_encrypted=encryptor.encrypt("refresh-b"),
        id_token_encrypted=encryptor.encrypt("id-b"),
        last_refresh=now,
        expires_at=fresh,
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )
    ...
    selection = await balancer.select_account()
    assert selection.account is not None
    assert selection.account.id == "acc_fresh"
```

```python
# tests/integration/test_proxy_api_extended.py
@pytest.mark.asyncio
async def test_proxy_ignores_expired_accounts_when_building_candidate_pool(async_client, db_setup):
    ...
    assert payload["error"]["code"] == "no_accounts"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_load_balancer_integration.py -k expired -v`
Expected: FAIL because expired active accounts are still eligible.

Run: `pytest tests/integration/test_proxy_api_extended.py -k expired -v`
Expected: FAIL because proxy candidate filtering ignores expiry.

- [ ] **Step 3: Centralize expiry-aware eligibility**

```python
# app/modules/proxy/helpers.py
from app.core.utils.time import utcnow


def is_account_expired(account: Account, *, now: datetime | None = None) -> bool:
    current = now or utcnow()
    return account.expires_at is not None and account.expires_at <= current


def _select_accounts_for_limits(accounts: Iterable[Account]) -> list[Account]:
    return [
        account
        for account in accounts
        if account.status not in (AccountStatus.DEACTIVATED, AccountStatus.PAUSED)
        and not is_account_expired(account)
    ]
```

```python
# app/core/openai/model_refresh_scheduler.py
if account.status != AccountStatus.ACTIVE or is_account_expired(account):
    continue
```

- [ ] **Step 4: Update direct query-based filters that bypass the helper**

```python
# app/modules/proxy/api.py
stmt = stmt.where(
    Account.status.notin_((AccountStatus.DEACTIVATED, AccountStatus.PAUSED)),
    or_(Account.expires_at.is_(None), Account.expires_at > utcnow()),
)
```

```python
# app/modules/proxy/load_balancer.py
all_accounts = [account for account in await repos.accounts.list_accounts() if not is_account_expired(account)]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/integration/test_load_balancer_integration.py -k expired -v`
Expected: PASS

Run: `pytest tests/integration/test_proxy_api_extended.py -k expired -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/modules/proxy/helpers.py app/modules/proxy/api.py app/modules/proxy/load_balancer.py app/core/openai/model_refresh_scheduler.py tests/integration/test_load_balancer_integration.py tests/integration/test_proxy_api_extended.py
git commit -m "feat(proxy): exclude expired accounts from selection"
```

### Task 4: Add frontend expiry types, mutations, and detail editing flow

**Files:**
- Modify: `frontend/src/features/accounts/schemas.ts`
- Modify: `frontend/src/features/accounts/api.ts`
- Modify: `frontend/src/features/accounts/hooks/use-accounts.ts`
- Modify: `frontend/src/features/accounts/components/accounts-page.tsx`
- Modify: `frontend/src/features/accounts/components/account-detail.tsx`
- Modify: `frontend/src/features/accounts/components/account-list-item.tsx`
- Create: `frontend/src/features/accounts/components/account-expiry-form.tsx`
- Test: `frontend/src/features/accounts/schemas.test.ts`
- Test: `frontend/src/features/accounts/components/account-detail.test.tsx`
- Test: `frontend/src/features/accounts/components/account-list-item.test.tsx`

- [ ] **Step 1: Write the failing frontend tests**

```tsx
// frontend/src/features/accounts/schemas.test.ts
it("parses expiry fields on account summary", () => {
  const parsed = AccountSummarySchema.parse({
    accountId: "acc-1",
    email: "user@example.com",
    displayName: "User",
    planType: "pro",
    status: "active",
    expiresAt: "2026-06-01T00:00:00+00:00",
    isExpired: false,
  });

  expect(parsed.expiresAt).toBe("2026-06-01T00:00:00+00:00");
  expect(parsed.isExpired).toBe(false);
});
```

```tsx
// frontend/src/features/accounts/components/account-list-item.test.tsx
it("shows expired badge copy", () => {
  const account = createAccountSummary({
    expiresAt: "2026-01-01T00:00:00+00:00",
    isExpired: true,
  });
  render(<AccountListItem account={account} selected={false} onSelect={vi.fn()} />);
  expect(screen.getByText("Expired")).toBeInTheDocument();
});
```

```tsx
// frontend/src/features/accounts/components/account-detail.test.tsx
it("submits expiry updates", async () => {
  const onUpdateExpiry = vi.fn().mockResolvedValue(undefined);
  render(
    <AccountDetail
      account={createAccountSummary({ expiresAt: null, isExpired: false })}
      busy={false}
      onPause={vi.fn()}
      onResume={vi.fn()}
      onDelete={vi.fn()}
      onReauth={vi.fn()}
      onUpdateExpiry={onUpdateExpiry}
    />,
  );

  await userEvent.click(screen.getByRole("button", { name: "Edit expiry" }));
  await userEvent.type(screen.getByLabelText("Expiry date"), "2026-06-01T00:00");
  await userEvent.click(screen.getByRole("button", { name: "Save expiry" }));

  expect(onUpdateExpiry).toHaveBeenCalledWith("acc-1", "2026-06-01T00:00:00.000Z");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/components/account-list-item.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx`
Expected: FAIL because expiry fields and edit UI do not exist.

- [ ] **Step 3: Extend schemas, API, and hooks**

```ts
// frontend/src/features/accounts/schemas.ts
export const AccountSummarySchema = z.object({
  ...
  expiresAt: z.string().datetime({ offset: true }).nullable().optional(),
  isExpired: z.boolean().default(false),
});

export const AccountExpiryUpdateRequestSchema = z.object({
  expiresAt: z.string().datetime({ offset: true }).nullable(),
});

export const AccountExpiryUpdateResponseSchema = z.object({
  accountId: z.string(),
  expiresAt: z.string().datetime({ offset: true }).nullable(),
  isExpired: z.boolean(),
});
```

```ts
// frontend/src/features/accounts/api.ts
export function updateAccountExpiry(accountId: string, expiresAt: string | null) {
  return patch(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}/expiry`,
    AccountExpiryUpdateResponseSchema,
    { body: AccountExpiryUpdateRequestSchema.parse({ expiresAt }) },
  );
}
```

```ts
// frontend/src/features/accounts/hooks/use-accounts.ts
const updateExpiryMutation = useMutation({
  mutationFn: ({ accountId, expiresAt }: { accountId: string; expiresAt: string | null }) =>
    updateAccountExpiry(accountId, expiresAt),
  onSuccess: () => {
    toast.success("Account expiry updated");
    invalidateAccountRelatedQueries(queryClient);
  },
});
```

- [ ] **Step 4: Build the expiry editor UI**

```tsx
// frontend/src/features/accounts/components/account-expiry-form.tsx
export function AccountExpiryForm({
  account,
  busy,
  onSave,
}: {
  account: AccountSummary;
  busy: boolean;
  onSave: (expiresAt: string | null) => Promise<void>;
}) {
  const [value, setValue] = useState(account.expiresAt ? account.expiresAt.slice(0, 16) : "");
  return (
    <form
      className="space-y-3 border-t pt-4"
      onSubmit={async (event) => {
        event.preventDefault();
        await onSave(value ? new Date(value).toISOString() : null);
      }}
    >
      <Label htmlFor="account-expiry">Expiry date</Label>
      <Input id="account-expiry" type="datetime-local" value={value} onChange={(event) => setValue(event.target.value)} />
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={busy}>Save expiry</Button>
        <Button type="button" size="sm" variant="outline" disabled={busy} onClick={() => void onSave(null)}>Clear expiry</Button>
      </div>
    </form>
  );
}
```

```tsx
// frontend/src/features/accounts/components/account-detail.tsx
export type AccountDetailProps = {
  ...
  onUpdateExpiry: (accountId: string, expiresAt: string | null) => Promise<void>;
};
...
<AccountExpiryForm
  account={account}
  busy={busy}
  onSave={(expiresAt) => onUpdateExpiry(account.accountId, expiresAt)}
/>
```

```tsx
// frontend/src/features/accounts/components/account-list-item.tsx
{account.isExpired ? (
  <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-700">
    Expired
  </span>
) : null}
```

- [ ] **Step 5: Wire the page-level mutation**

```tsx
// frontend/src/features/accounts/components/accounts-page.tsx
const mutationBusy =
  importMutation.isPending ||
  pauseMutation.isPending ||
  resumeMutation.isPending ||
  deleteMutation.isPending ||
  updateExpiryMutation.isPending;
...
<AccountDetail
  ...
  onUpdateExpiry={(accountId, expiresAt) => updateExpiryMutation.mutateAsync({ accountId, expiresAt })}
/>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/components/account-list-item.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/features/accounts/schemas.ts frontend/src/features/accounts/api.ts frontend/src/features/accounts/hooks/use-accounts.ts frontend/src/features/accounts/components/accounts-page.tsx frontend/src/features/accounts/components/account-detail.tsx frontend/src/features/accounts/components/account-list-item.tsx frontend/src/features/accounts/components/account-expiry-form.tsx frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/components/account-detail.test.tsx frontend/src/features/accounts/components/account-list-item.test.tsx
git commit -m "feat(frontend): add account expiry editing"
```

### Task 5: Run end-to-end verification and align OpenSpec task state

**Files:**
- Modify: `openspec/changes/add-account-expiry-dates/tasks.md`
- Test: `tests/integration/test_accounts_api.py`
- Test: `tests/integration/test_accounts_api_extended.py`
- Test: `tests/integration/test_load_balancer_integration.py`
- Test: `tests/integration/test_proxy_api_extended.py`
- Test: `frontend/src/features/accounts/schemas.test.ts`
- Test: `frontend/src/features/accounts/components/account-list-item.test.tsx`
- Test: `frontend/src/features/accounts/components/account-detail.test.tsx`
- Test: `frontend/src/__integration__/accounts-flow.test.tsx`

- [ ] **Step 1: Add the failing integration test for the user-facing flow**

```tsx
// frontend/src/__integration__/accounts-flow.test.tsx
it("shows and updates account expiry from the accounts page", async () => {
  window.history.pushState({}, "", "/accounts");
  renderWithProviders(<App />);

  expect(await screen.findByRole("heading", { name: "Accounts" })).toBeInTheDocument();
  await userEvent.click(await screen.findByText("primary@example.com"));
  await userEvent.click(screen.getByRole("button", { name: "Edit expiry" }));
  await userEvent.type(screen.getByLabelText("Expiry date"), "2026-06-01T00:00");
  await userEvent.click(screen.getByRole("button", { name: "Save expiry" }));

  expect(await screen.findByText(/Expires/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the new integration test to verify it fails**

Run: `pnpm vitest run frontend/src/__integration__/accounts-flow.test.tsx`
Expected: FAIL because the expiry UI is not present before implementation.

- [ ] **Step 3: Run focused backend and frontend suites after implementation**

```bash
pytest tests/integration/test_accounts_api.py tests/integration/test_accounts_api_extended.py tests/integration/test_load_balancer_integration.py tests/integration/test_proxy_api_extended.py -q
pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/components/account-list-item.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx frontend/src/__integration__/accounts-flow.test.tsx
openspec validate --specs
```

Expected: all commands PASS.

- [ ] **Step 4: Mark the OpenSpec task checklist**

```md
## 1. OpenSpec and data model

- [x] 1.1 Add the `account-expiry` proposal/spec/design artifacts for account-level expiry behavior.
- [x] 1.2 Add database support for nullable `accounts.expires_at`.
...
```

- [ ] **Step 5: Commit**

```bash
git add openspec/changes/add-account-expiry-dates/tasks.md frontend/src/__integration__/accounts-flow.test.tsx
git commit -m "test(accounts): verify account expiry flow"
```
