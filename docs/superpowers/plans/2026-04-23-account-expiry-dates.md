# Account Expiry Dates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add account-level expiry dates that default to 30 days on add/import, round-trip through portable import/export, stay editable from `/accounts`, and exclude expired accounts from normal routing without mutating lifecycle status.

**Architecture:** Persist a dedicated nullable `accounts.expires_at` field, expose `expiresAt` and derived `isExpired` on account APIs, and centralize expiry decisions in backend service/selection code. Reuse the existing portable account normalization boundary for import/export and reuse the existing frontend expiry picker pattern to keep the UI change focused.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, React, TanStack Query, Zod, Vitest, Testing Library, pytest

---

## File Structure

- Modify: `app/db/models.py`
  Responsibility: add the persisted `Account.expires_at` field.
- Create: `app/db/alembic/versions/20260423_000000_add_accounts_expires_at.py`
  Responsibility: schema migration for nullable account expiry.
- Modify: `app/modules/accounts/schemas.py`
  Responsibility: add `expires_at`/`is_expired` response fields and expiry-update request/response models.
- Modify: `app/modules/accounts/mappers.py`
  Responsibility: map persisted expiry into account summaries and compute backend-owned `is_expired`.
- Modify: `app/modules/accounts/repository.py`
  Responsibility: add focused expiry update support and pass expiry through `upsert`.
- Modify: `app/modules/accounts/service.py`
  Responsibility: default expiry on add/import, preserve portable expiry, reset expiry on re-import without payload expiry, export expiry, and update expiry manually.
- Modify: `app/modules/accounts/portable.py`
  Responsibility: parse/export portable expiry values.
- Modify: `app/modules/accounts/api.py`
  Responsibility: expose the new expiry update endpoint.
- Modify: `app/modules/proxy/load_balancer.py`
  Responsibility: exclude expired accounts from normal selection input.
- Modify: `app/modules/proxy/api.py`
  Responsibility: exclude expired accounts from usage-limit/account-loading helper paths that define “available accounts”.
- Modify: `frontend/src/features/accounts/schemas.ts`
  Responsibility: accept `expiresAt` and `isExpired`, plus expiry update request/response.
- Modify: `frontend/src/features/accounts/api.ts`
  Responsibility: add account expiry update API call.
- Modify: `frontend/src/features/accounts/hooks/use-accounts.ts`
  Responsibility: add expiry mutation and shared invalidation.
- Modify: `frontend/src/features/accounts/components/accounts-page.tsx`
  Responsibility: wire the expiry edit dialog into page state.
- Modify: `frontend/src/features/accounts/components/account-list-item.tsx`
  Responsibility: show expiry state in the left-pane list.
- Modify: `frontend/src/features/accounts/components/account-detail.tsx`
  Responsibility: show expiry value/state and launch the editor.
- Create: `frontend/src/features/accounts/components/account-expiry-dialog.tsx`
  Responsibility: focused set/extend/clear expiry editor using the existing expiry picker.
- Modify: `tests/integration/test_accounts_api.py`
  Responsibility: API-level expiry list/update coverage.
- Modify: `tests/integration/test_accounts_api_extended.py`
  Responsibility: import/export expiry behavior and portable round-tripping.
- Modify: `tests/integration/test_load_balancer_integration.py`
  Responsibility: routing exclusion coverage for expired accounts.
- Modify: `frontend/src/features/accounts/schemas.test.ts`
  Responsibility: schema coverage for new account expiry fields.
- Modify: `frontend/src/features/accounts/api.test.ts`
  Responsibility: API client coverage for expiry update calls.
- Modify: `frontend/src/features/accounts/components/account-list.test.tsx`
  Responsibility: left-pane expiry state coverage.
- Create: `frontend/src/features/accounts/components/account-expiry-dialog.test.tsx`
  Responsibility: dialog submit/clear behavior.
- Create: `frontend/src/features/accounts/components/account-detail.test.tsx`
  Responsibility: detail-surface expiry rendering and edit affordance.

### Task 1: Persist Account Expiry And Expose It Through Accounts API

**Files:**
- Create: `app/db/alembic/versions/20260423_000000_add_accounts_expires_at.py`
- Modify: `app/db/models.py`
- Modify: `app/modules/accounts/schemas.py`
- Modify: `app/modules/accounts/mappers.py`
- Modify: `app/modules/accounts/repository.py`
- Modify: `app/modules/accounts/service.py`
- Modify: `app/modules/accounts/api.py`
- Test: `tests/integration/test_accounts_api.py`

- [ ] **Step 1: Write the failing integration tests for list and manual expiry update**

```python
@pytest.mark.asyncio
async def test_list_accounts_includes_expiry_state(async_client):
    auth_json = _make_auth_json("acc_expiry", "expiry@example.com")
    create = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(auth_json), "application/json")},
    )
    assert create.status_code == 200

    account_id = create.json()["accountId"]
    expires_at = "2026-05-23T15:00:00Z"
    patch = await async_client.patch(
        f"/api/accounts/{account_id}/expiry",
        json={"expiresAt": expires_at},
    )
    assert patch.status_code == 200

    listing = await async_client.get("/api/accounts")
    assert listing.status_code == 200
    row = next(item for item in listing.json()["accounts"] if item["accountId"] == account_id)
    assert row["expiresAt"] == expires_at
    assert row["isExpired"] is False


@pytest.mark.asyncio
async def test_patch_account_expiry_can_clear_value(async_client):
    auth_json = _make_auth_json("acc_clear_expiry", "clear-expiry@example.com")
    create = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(auth_json), "application/json")},
    )
    account_id = create.json()["accountId"]

    first = await async_client.patch(
        f"/api/accounts/{account_id}/expiry",
        json={"expiresAt": "2026-05-23T15:00:00Z"},
    )
    assert first.status_code == 200

    second = await async_client.patch(
        f"/api/accounts/{account_id}/expiry",
        json={"expiresAt": None},
    )
    assert second.status_code == 200
    assert second.json()["expiresAt"] is None
    assert second.json()["isExpired"] is False


@pytest.mark.asyncio
async def test_patch_account_expiry_returns_404_for_missing_account(async_client):
    response = await async_client.patch(
        "/api/accounts/missing/expiry",
        json={"expiresAt": "2026-05-23T15:00:00Z"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"
```

- [ ] **Step 2: Run the backend test slice to verify it fails on the missing contract**

Run: `pytest tests/integration/test_accounts_api.py -k "expiry" -v`
Expected: FAIL with `405 Method Not Allowed`, schema mismatches, or missing `expiresAt` / `isExpired` fields.

- [ ] **Step 3: Add the persisted field, request/response models, mapper fields, repository update hook, and API route**

```python
# app/db/models.py
class Account(Base):
    __tablename__ = "accounts"
    # ...
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[AccountStatus] = mapped_column(...)


# app/modules/accounts/schemas.py
class AccountSummary(DashboardModel):
    account_id: str
    email: str
    display_name: str
    plan_type: str
    status: str
    expires_at: datetime | None = None
    is_expired: bool = False
    # existing fields...


class AccountExpiryUpdateRequest(DashboardModel):
    expires_at: datetime | None = Field(default=None, alias="expiresAt")


class AccountExpiryResponse(DashboardModel):
    account_id: str = Field(alias="accountId")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    is_expired: bool = Field(alias="isExpired")


# app/modules/accounts/mappers.py
from app.core.utils.time import to_utc_naive, utcnow


def _account_is_expired(account: Account, *, now: datetime | None = None) -> bool:
    if account.expires_at is None:
        return False
    comparison_now = to_utc_naive(now or utcnow())
    return to_utc_naive(account.expires_at) <= comparison_now


return AccountSummary(
    account_id=account.id,
    email=account.email,
    display_name=account.email,
    plan_type=plan_type,
    status=account.status.value,
    expires_at=account.expires_at,
    is_expired=_account_is_expired(account),
    # existing fields...
)


# app/modules/accounts/repository.py
async def update_expiry(self, account_id: str, *, expires_at: datetime | None) -> Account | None:
    result = await self._session.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(expires_at=expires_at)
        .returning(Account)
    )
    await self._session.commit()
    return result.scalar_one_or_none()


# app/modules/accounts/service.py
async def update_account_expiry(self, account_id: str, *, expires_at: datetime | None) -> AccountSummary | None:
    normalized = to_utc_naive(expires_at)
    updated = await self._repo.update_expiry(account_id, expires_at=normalized)
    if updated is None:
        return None
    get_account_selection_cache().invalidate()
    return build_account_summaries(
        accounts=[updated],
        primary_usage={},
        secondary_usage={},
        request_usage_by_account={},
        additional_quotas_by_account={},
        encryptor=self._encryptor,
    )[0]


# app/modules/accounts/api.py
@router.patch("/{account_id}/expiry", response_model=AccountExpiryResponse)
async def update_account_expiry(
    account_id: str,
    payload: AccountExpiryUpdateRequest,
    context: AccountsContext = Depends(get_accounts_context),
) -> AccountExpiryResponse:
    updated = await context.service.update_account_expiry(account_id, expires_at=payload.expires_at)
    if updated is None:
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return AccountExpiryResponse(
        accountId=updated.account_id,
        expiresAt=updated.expires_at,
        isExpired=updated.is_expired,
    )
```

- [ ] **Step 4: Add the migration for nullable `accounts.expires_at`**

```python
"""add accounts expires_at

Revision ID: 20260423_000000
Revises: 20260419_020000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_000000"
down_revision = "20260419_020000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("expires_at")
```

- [ ] **Step 5: Run the backend test slice again**

Run: `pytest tests/integration/test_accounts_api.py -k "expiry" -v`
Expected: PASS for the new expiry tests.

- [ ] **Step 6: Commit the persistence/API contract slice**

```bash
git add app/db/models.py \
  app/db/alembic/versions/20260423_000000_add_accounts_expires_at.py \
  app/modules/accounts/schemas.py \
  app/modules/accounts/mappers.py \
  app/modules/accounts/repository.py \
  app/modules/accounts/service.py \
  app/modules/accounts/api.py \
  tests/integration/test_accounts_api.py
git commit -m "feat(accounts): add account expiry contract"
```

### Task 2: Add Defaulting And Portable Import/Export Round-Tripping

**Files:**
- Modify: `app/modules/accounts/portable.py`
- Modify: `app/modules/accounts/service.py`
- Modify: `app/modules/accounts/repository.py`
- Test: `tests/integration/test_accounts_api_extended.py`

- [ ] **Step 1: Write the failing integration tests for defaulting, preserve, reset, and export**

```python
@pytest.mark.asyncio
async def test_auth_json_import_defaults_expiry_to_30_days(async_client):
    before = utcnow()
    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(_make_auth_json("acc_default_expiry", "default-expiry@example.com")), "application/json")},
    )
    assert response.status_code == 200

    listing = await async_client.get("/api/accounts")
    row = next(item for item in listing.json()["accounts"] if item["email"] == "default-expiry@example.com")
    expires_at = datetime.fromisoformat(row["expiresAt"].replace("Z", "+00:00"))
    lower_bound = before.replace(tzinfo=timezone.utc) + timedelta(days=29, hours=23)
    upper_bound = before.replace(tzinfo=timezone.utc) + timedelta(days=30, minutes=5)
    assert lower_bound <= expires_at <= upper_bound
    assert row["isExpired"] is False


@pytest.mark.asyncio
async def test_portable_import_preserves_supplied_expiry(async_client):
    portable = [_make_portable_account_record("acc_portable_expiry", "portable-expiry@example.com", "plus")]
    portable[0]["expires_at"] = "2026-06-01T00:00:00Z"
    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("portable.json", json.dumps(portable), "application/json")},
    )
    assert response.status_code == 200

    listing = await async_client.get("/api/accounts")
    row = next(item for item in listing.json()["accounts"] if item["email"] == "portable-expiry@example.com")
    assert row["expiresAt"] == "2026-06-01T00:00:00Z"


@pytest.mark.asyncio
async def test_reimport_without_expiry_resets_lease_to_30_days(async_client):
    first_payload = [_make_portable_account_record("acc_reset_lease", "reset-lease@example.com", "plus")]
    first_payload[0]["expires_at"] = "2026-05-01T00:00:00Z"
    first = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("portable.json", json.dumps(first_payload), "application/json")},
    )
    assert first.status_code == 200

    second_payload = [_make_portable_account_record("acc_reset_lease", "reset-lease@example.com", "plus")]
    second = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("portable.json", json.dumps(second_payload), "application/json")},
    )
    assert second.status_code == 200

    listing = await async_client.get("/api/accounts")
    row = next(item for item in listing.json()["accounts"] if item["email"] == "reset-lease@example.com")
    assert row["expiresAt"] != "2026-05-01T00:00:00Z"


@pytest.mark.asyncio
async def test_export_portable_accounts_includes_expiry(async_client):
    await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(_make_auth_json("acc_export_expiry", "export-expiry@example.com")), "application/json")},
    )
    listing = await async_client.get("/api/accounts")
    account_id = next(item["accountId"] for item in listing.json()["accounts"] if item["email"] == "export-expiry@example.com")
    await async_client.patch(f"/api/accounts/{account_id}/expiry", json={"expiresAt": "2026-06-15T00:00:00Z"})

    exported = await async_client.get("/api/accounts/export")
    assert exported.status_code == 200
    payload = exported.json()
    row = next(item for item in payload if item["email"] == "export-expiry@example.com")
    assert row["expires_at"] == "2026-06-15T00:00:00Z"
```

- [ ] **Step 2: Run the import/export expiry slice to verify it fails**

Run: `pytest tests/integration/test_accounts_api_extended.py -k "expiry" -v`
Expected: FAIL because portable records ignore expiry and auth/import paths do not default expiry yet.

- [ ] **Step 3: Thread expiry through portable models and import/export service logic**

```python
# app/modules/accounts/portable.py
class PortableAccountRecord(BaseModel):
    source_id: str | None = None
    email: str
    plan_type: str
    raw_account_id: str | None = None
    id_token: str
    access_token: str
    refresh_token: str
    last_refresh_at: datetime | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class PortableExternalAccountImport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # existing fields...
    expires_at: datetime | None = None


class PortableExternalAccountExport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # existing fields...
    expires_at: datetime | None = None


def portable_record_from_external_account(account: PortableExternalAccountImport) -> PortableAccountRecord:
    return PortableAccountRecord(
        source_id=account.id,
        email=claims.email or account.email or DEFAULT_EMAIL,
        plan_type=coerce_account_plan_type(claims.plan_type or account.plan_type, DEFAULT_PLAN),
        raw_account_id=claims.account_id or account.account_id,
        id_token=account.tokens.id_token,
        access_token=account.tokens.access_token,
        refresh_token=account.tokens.refresh_token,
        last_refresh_at=_best_external_timestamp(account),
        created_at=_epoch_to_utc_naive(account.created_at),
        expires_at=_to_utc_naive(account.expires_at),
    )


def build_portable_export_account(..., expires_at: datetime | None,) -> PortableExternalAccountExport:
    return PortableExternalAccountExport(
        # existing fields...
        expires_at=_datetime_to_iso8601(expires_at),
    )


# app/modules/accounts/service.py
_DEFAULT_ACCOUNT_EXPIRY_DAYS = 30


def _resolve_import_expiry(portable_account: PortableAccountRecord) -> datetime:
    supplied = to_utc_naive(portable_account.expires_at)
    if supplied is not None:
        return supplied
    return utcnow() + timedelta(days=_DEFAULT_ACCOUNT_EXPIRY_DAYS)


account = Account(
    id=account_id,
    chatgpt_account_id=raw_account_id,
    email=email,
    plan_type=portable_account.plan_type,
    access_token_encrypted=self._encryptor.encrypt(portable_account.access_token),
    refresh_token_encrypted=self._encryptor.encrypt(portable_account.refresh_token),
    id_token_encrypted=self._encryptor.encrypt(portable_account.id_token),
    last_refresh=portable_account.last_refresh_at or utcnow(),
    expires_at=_resolve_import_expiry(portable_account),
    status=AccountStatus.ACTIVE,
    deactivation_reason=None,
)

payload = [
    build_portable_export_account(
        stored_account_id=account.id,
        email=account.email,
        plan_type=account.plan_type,
        raw_account_id=account.chatgpt_account_id,
        id_token=self._encryptor.decrypt(account.id_token_encrypted),
        access_token=self._encryptor.decrypt(account.access_token_encrypted),
        refresh_token=self._encryptor.decrypt(account.refresh_token_encrypted),
        created_at=account.created_at,
        last_refresh_at=account.last_refresh,
        expires_at=account.expires_at,
    ).model_dump(mode="json")
    for account in accounts
]
```

- [ ] **Step 4: Ensure re-import updates expiry even when the payload omits it**

```python
# app/modules/accounts/repository.py
def _apply_account_updates(target: Account, source: Account) -> None:
    target.chatgpt_account_id = source.chatgpt_account_id
    target.email = source.email
    target.plan_type = source.plan_type
    target.access_token_encrypted = source.access_token_encrypted
    target.refresh_token_encrypted = source.refresh_token_encrypted
    target.id_token_encrypted = source.id_token_encrypted
    target.last_refresh = source.last_refresh
    target.expires_at = source.expires_at
```

- [ ] **Step 5: Run the import/export expiry tests again**

Run: `pytest tests/integration/test_accounts_api_extended.py -k "expiry" -v`
Expected: PASS for defaulting, preserve, reset, and export cases.

- [ ] **Step 6: Commit the import/export slice**

```bash
git add app/modules/accounts/portable.py \
  app/modules/accounts/service.py \
  app/modules/accounts/repository.py \
  tests/integration/test_accounts_api_extended.py
git commit -m "feat(accounts): round-trip account expiry in imports"
```

### Task 3: Exclude Expired Accounts From Normal Routing

**Files:**
- Modify: `app/modules/proxy/load_balancer.py`
- Modify: `app/modules/proxy/api.py`
- Optionally Modify: `app/modules/accounts/mappers.py`
- Test: `tests/integration/test_load_balancer_integration.py`

- [ ] **Step 1: Write the failing routing tests for expired accounts**

```python
@pytest.mark.asyncio
async def test_load_balancer_skips_expired_accounts(db_setup):
    encryptor = TokenEncryptor()
    now = utcnow()
    expired = Account(
        id="acc_expired",
        email="expired@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access-expired"),
        refresh_token_encrypted=encryptor.encrypt("refresh-expired"),
        id_token_encrypted=encryptor.encrypt("id-expired"),
        last_refresh=now,
        expires_at=now - timedelta(minutes=1),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )
    active = Account(
        id="acc_active",
        email="active@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access-active"),
        refresh_token_encrypted=encryptor.encrypt("refresh-active"),
        id_token_encrypted=encryptor.encrypt("id-active"),
        last_refresh=now,
        expires_at=now + timedelta(days=1),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )

    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        await accounts_repo.upsert(expired)
        await accounts_repo.upsert(active)

        balancer = LoadBalancer(_repo_factory)
        selection = await balancer.select_account()

        assert selection.account is not None
        assert selection.account.id == "acc_active"


@pytest.mark.asyncio
async def test_load_balancer_returns_no_accounts_when_only_expired_accounts_exist(db_setup):
    encryptor = TokenEncryptor()
    now = utcnow()
    expired = Account(
        id="acc_only_expired",
        email="only-expired@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=now,
        expires_at=now - timedelta(minutes=1),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )

    async with SessionLocal() as session:
        accounts_repo = AccountsRepository(session)
        await accounts_repo.upsert(expired)

        balancer = LoadBalancer(_repo_factory)
        selection = await balancer.select_account()

        assert selection.account is None
        assert selection.error_message == "No active accounts available" or selection.error_message == "No available accounts"
```

- [ ] **Step 2: Run the routing slice to verify it fails**

Run: `pytest tests/integration/test_load_balancer_integration.py -k "expired" -v`
Expected: FAIL because active-but-expired accounts are still eligible today.

- [ ] **Step 3: Filter expired accounts in the shared load-balancer input path**

```python
# app/modules/proxy/load_balancer.py
from app.core.utils.time import to_utc_naive, utcnow


def _is_account_expired(account: Account, *, now: datetime | None = None) -> bool:
    if account.expires_at is None:
        return False
    comparison_now = to_utc_naive(now or utcnow())
    return to_utc_naive(account.expires_at) <= comparison_now


async def load_selection_inputs() -> _SelectionInputs:
    selection_inputs = await self._load_selection_inputs(...)
    active_candidates = [
        account for account in selection_inputs.accounts
        if not _is_account_expired(account)
    ]
    if len(active_candidates) != len(selection_inputs.accounts):
        selection_inputs = _SelectionInputs(
            accounts=active_candidates,
            latest_primary=selection_inputs.latest_primary,
            latest_secondary=selection_inputs.latest_secondary,
            runtime_accounts=selection_inputs.runtime_accounts,
            error_message=selection_inputs.error_message,
            error_code=selection_inputs.error_code,
        )
    return selection_inputs
```

- [ ] **Step 4: Filter expired accounts in the proxy helper that defines “available accounts”**

```python
# app/modules/proxy/api.py
result = await session.execute(
    select(Account).where(
        Account.id.in_(account_ids),
        Account.status.notin_((AccountStatus.DEACTIVATED, AccountStatus.PAUSED)),
        or_(Account.expires_at.is_(None), Account.expires_at > utcnow()),
    )
)
return list(result.scalars().all())
```

- [ ] **Step 5: Run the routing tests again**

Run: `pytest tests/integration/test_load_balancer_integration.py -k "expired" -v`
Expected: PASS for both skip-expired and only-expired paths.

- [ ] **Step 6: Commit the routing exclusion slice**

```bash
git add app/modules/proxy/load_balancer.py \
  app/modules/proxy/api.py \
  tests/integration/test_load_balancer_integration.py
git commit -m "feat(proxy): exclude expired accounts from routing"
```

### Task 4: Add Frontend Schema, API, And Mutation Support

**Files:**
- Modify: `frontend/src/features/accounts/schemas.ts`
- Modify: `frontend/src/features/accounts/api.ts`
- Modify: `frontend/src/features/accounts/hooks/use-accounts.ts`
- Modify: `frontend/src/features/accounts/schemas.test.ts`
- Modify: `frontend/src/features/accounts/api.test.ts`

- [ ] **Step 1: Write the failing frontend contract tests**

```ts
// frontend/src/features/accounts/schemas.test.ts
it("parses account expiry fields", () => {
  const parsed = AccountSummarySchema.parse({
    accountId: "acc-1",
    email: "user@example.com",
    displayName: "User",
    planType: "pro",
    status: "active",
    expiresAt: "2026-06-01T00:00:00Z",
    isExpired: false,
    additionalQuotas: [],
  });

  expect(parsed.expiresAt).toBe("2026-06-01T00:00:00Z");
  expect(parsed.isExpired).toBe(false);
});


// frontend/src/features/accounts/api.test.ts
it("patches account expiry", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        accountId: "acc-1",
        expiresAt: "2026-06-01T00:00:00Z",
        isExpired: false,
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  const result = await updateAccountExpiry("acc-1", { expiresAt: "2026-06-01T00:00:00Z" });

  expect(fetchSpy).toHaveBeenCalledWith(
    "/api/accounts/acc-1/expiry",
    expect.objectContaining({ method: "PATCH", credentials: "same-origin" }),
  );
  expect(result.expiresAt).toBe("2026-06-01T00:00:00Z");
  fetchSpy.mockRestore();
});
```

- [ ] **Step 2: Run the frontend contract tests to verify they fail**

Run: `pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/api.test.ts`
Expected: FAIL because the schemas and API client do not know about account expiry yet.

- [ ] **Step 3: Add the Zod schemas and expiry update API helper**

```ts
// frontend/src/features/accounts/schemas.ts
export const AccountSummarySchema = z.object({
  accountId: z.string(),
  email: z.string(),
  displayName: z.string(),
  planType: z.string(),
  status: z.string(),
  expiresAt: z.string().datetime({ offset: true }).nullable().optional(),
  isExpired: z.boolean().default(false),
  // existing fields...
});

export const AccountExpiryUpdateRequestSchema = z.object({
  expiresAt: z.string().datetime({ offset: true }).nullable(),
});

export const AccountExpiryResponseSchema = z.object({
  accountId: z.string(),
  expiresAt: z.string().datetime({ offset: true }).nullable(),
  isExpired: z.boolean(),
});

export type AccountExpiryUpdateRequest = z.infer<typeof AccountExpiryUpdateRequestSchema>;
export type AccountExpiryResponse = z.infer<typeof AccountExpiryResponseSchema>;


// frontend/src/features/accounts/api.ts
import {
  AccountActionResponseSchema,
  AccountExpiryResponseSchema,
  AccountExpiryUpdateRequestSchema,
  // existing imports...
} from "@/features/accounts/schemas";

export function updateAccountExpiry(accountId: string, payload: unknown) {
  const validated = AccountExpiryUpdateRequestSchema.parse(payload);
  return patch(
    `${ACCOUNTS_BASE_PATH}/${encodeURIComponent(accountId)}/expiry`,
    AccountExpiryResponseSchema,
    { body: validated },
  );
}
```

- [ ] **Step 4: Add the expiry mutation and shared invalidation**

```ts
// frontend/src/features/accounts/hooks/use-accounts.ts
import {
  deleteAccount,
  exportAccounts,
  getAccountTrends,
  importAccount,
  listAccounts,
  pauseAccount,
  reactivateAccount,
  updateAccountExpiry,
} from "@/features/accounts/api";

const expiryMutation = useMutation({
  mutationFn: ({ accountId, expiresAt }: { accountId: string; expiresAt: string | null }) =>
    updateAccountExpiry(accountId, { expiresAt }),
  onSuccess: () => {
    toast.success("Account expiry updated");
    invalidateAccountRelatedQueries(queryClient);
  },
  onError: (error: Error) => {
    toast.error(error.message || "Failed to update expiry");
  },
});

return {
  importMutation,
  exportMutation,
  pauseMutation,
  resumeMutation,
  deleteMutation,
  expiryMutation,
};
```

- [ ] **Step 5: Re-run the frontend contract tests**

Run: `pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/api.test.ts`
Expected: PASS.

- [ ] **Step 6: Commit the frontend plumbing slice**

```bash
git add frontend/src/features/accounts/schemas.ts \
  frontend/src/features/accounts/api.ts \
  frontend/src/features/accounts/hooks/use-accounts.ts \
  frontend/src/features/accounts/schemas.test.ts \
  frontend/src/features/accounts/api.test.ts
git commit -m "feat(accounts): add frontend expiry plumbing"
```

### Task 5: Add Expiry UI To Account Detail And List

**Files:**
- Create: `frontend/src/features/accounts/components/account-expiry-dialog.tsx`
- Create: `frontend/src/features/accounts/components/account-expiry-dialog.test.tsx`
- Create: `frontend/src/features/accounts/components/account-detail.test.tsx`
- Modify: `frontend/src/features/accounts/components/account-detail.tsx`
- Modify: `frontend/src/features/accounts/components/account-list-item.tsx`
- Modify: `frontend/src/features/accounts/components/accounts-page.tsx`
- Modify: `frontend/src/features/accounts/components/account-list.test.tsx`

- [ ] **Step 1: Write the failing UI tests**

```ts
// frontend/src/features/accounts/components/account-list.test.tsx
it("shows expired state in the account list", () => {
  render(
    <AccountList
      accounts={[
        {
          accountId: "acc-expired",
          email: "expired@example.com",
          displayName: "Expired",
          planType: "plus",
          status: "active",
          expiresAt: "2026-04-01T00:00:00Z",
          isExpired: true,
          additionalQuotas: [],
        },
      ]}
      selectedAccountId="acc-expired"
      onSelect={() => {}}
      onOpenImport={() => {}}
      onExport={() => {}}
      onOpenOauth={() => {}}
    />,
  );

  expect(screen.getByText("Expired")).toBeInTheDocument();
  expect(screen.getByText("Expired")).toBeInTheDocument();
});


// frontend/src/features/accounts/components/account-detail.test.tsx
it("renders expiry and edit affordance", async () => {
  const user = userEvent.setup();
  const onEditExpiry = vi.fn();

  render(
    <AccountDetail
      account={{
        accountId: "acc-1",
        email: "user@example.com",
        displayName: "User",
        planType: "plus",
        status: "active",
        expiresAt: "2026-06-01T00:00:00Z",
        isExpired: false,
        additionalQuotas: [],
      }}
      busy={false}
      onPause={() => {}}
      onResume={() => {}}
      onDelete={() => {}}
      onReauth={() => {}}
      onEditExpiry={onEditExpiry}
    />,
  );

  expect(screen.getByText(/expires/i)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /edit expiry/i }));
  expect(onEditExpiry).toHaveBeenCalledTimes(1);
});


// frontend/src/features/accounts/components/account-expiry-dialog.test.tsx
it("submits a cleared expiry", async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn().mockResolvedValue(undefined);

  render(
    <AccountExpiryDialog
      open
      busy={false}
      accountEmail="user@example.com"
      initialValue="2026-06-01T00:00:00Z"
      onOpenChange={() => {}}
      onSubmit={onSubmit}
    />,
  );

  await user.click(screen.getByRole("button", { name: /no expiration/i }));
  await user.click(screen.getByRole("button", { name: /save expiry/i }));

  expect(onSubmit).toHaveBeenCalledWith({ expiresAt: null });
});
```

- [ ] **Step 2: Run the UI tests to verify they fail**

Run: `pnpm vitest run frontend/src/features/accounts/components/account-list.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx frontend/src/features/accounts/components/account-expiry-dialog.test.tsx`
Expected: FAIL because the expiry UI components and props do not exist yet.

- [ ] **Step 3: Add a focused expiry dialog that reuses the existing `ExpiryPicker`**

```tsx
// frontend/src/features/accounts/components/account-expiry-dialog.tsx
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ExpiryPicker } from "@/features/api-keys/components/expiry-picker";
import { parseDate } from "@/utils/formatters";

export type AccountExpiryDialogProps = {
  open: boolean;
  busy: boolean;
  accountEmail: string;
  initialValue: string | null | undefined;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: { expiresAt: string | null }) => Promise<void>;
};

export function AccountExpiryDialog({
  open,
  busy,
  accountEmail,
  initialValue,
  onOpenChange,
  onSubmit,
}: AccountExpiryDialogProps) {
  const [expiresAt, setExpiresAt] = useState<Date | null>(() => parseDate(initialValue ?? null));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit account expiry</DialogTitle>
          <DialogDescription>
            Update when {accountEmail} should stop being used for normal routing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <div className="text-sm font-medium">Expiry</div>
          <ExpiryPicker value={expiresAt} onChange={setExpiresAt} />
        </div>

        <DialogFooter>
          <Button
            type="button"
            onClick={async () => {
              await onSubmit({ expiresAt: expiresAt?.toISOString() ?? null });
              onOpenChange(false);
            }}
            disabled={busy}
          >
            Save expiry
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Thread expiry state through detail, list, and page wiring**

```tsx
// frontend/src/features/accounts/components/account-detail.tsx
export type AccountDetailProps = {
  account: AccountSummary | null;
  showAccountId?: boolean;
  busy: boolean;
  onPause: (accountId: string) => void;
  onResume: (accountId: string) => void;
  onDelete: (accountId: string) => void;
  onReauth: () => void;
  onEditExpiry: () => void;
};

// inside the selected-account branch
<div className="rounded-lg border bg-muted/30 p-3">
  <div className="flex items-center justify-between gap-3">
    <div>
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Expiry</p>
      <p className="text-sm">
        {account.expiresAt ? formatExpiry(account.expiresAt) : "No expiration"}
      </p>
      {account.isExpired ? (
        <p className="mt-1 text-xs text-amber-600">Expired accounts stay visible here but are excluded from normal routing.</p>
      ) : null}
    </div>
    <Button type="button" size="sm" variant="outline" onClick={onEditExpiry} disabled={busy}>
      Edit expiry
    </Button>
  </div>
</div>


// frontend/src/features/accounts/components/account-list-item.tsx
const expiryText = account.isExpired
  ? "Expired"
  : account.expiresAt
    ? `Expires ${formatDateOnly(account.expiresAt)}`
    : "No expiry";

<p className="mt-1 truncate text-[11px] text-muted-foreground">{expiryText}</p>


// frontend/src/features/accounts/components/accounts-page.tsx
const expiryDialog = useDialogState();

const mutationBusy =
  importMutation.isPending ||
  pauseMutation.isPending ||
  resumeMutation.isPending ||
  deleteMutation.isPending ||
  expiryMutation.isPending;

<AccountDetail
  account={selectedAccount}
  showAccountId={selectedAccount ? duplicateAccountIds.has(selectedAccount.accountId) : false}
  busy={mutationBusy}
  onPause={(accountId) => void pauseMutation.mutateAsync(accountId)}
  onResume={(accountId) => void resumeMutation.mutateAsync(accountId)}
  onDelete={(accountId) => deleteDialog.show(accountId)}
  onReauth={() => oauthDialog.show()}
  onEditExpiry={() => expiryDialog.show()}
/>

<AccountExpiryDialog
  open={expiryDialog.open}
  busy={expiryMutation.isPending}
  accountEmail={selectedAccount?.email ?? ""}
  initialValue={selectedAccount?.expiresAt ?? null}
  onOpenChange={expiryDialog.onOpenChange}
  onSubmit={async ({ expiresAt }) => {
    if (!selectedAccount) return;
    await expiryMutation.mutateAsync({ accountId: selectedAccount.accountId, expiresAt });
  }}
/>
```

- [ ] **Step 5: Run the UI tests again**

Run: `pnpm vitest run frontend/src/features/accounts/components/account-list.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx frontend/src/features/accounts/components/account-expiry-dialog.test.tsx frontend/src/__integration__/accounts-flow.test.tsx`
Expected: PASS.

- [ ] **Step 6: Commit the UI slice**

```bash
git add frontend/src/features/accounts/components/account-expiry-dialog.tsx \
  frontend/src/features/accounts/components/account-expiry-dialog.test.tsx \
  frontend/src/features/accounts/components/account-detail.tsx \
  frontend/src/features/accounts/components/account-detail.test.tsx \
  frontend/src/features/accounts/components/account-list-item.tsx \
  frontend/src/features/accounts/components/account-list.test.tsx \
  frontend/src/features/accounts/components/accounts-page.tsx \
  frontend/src/__integration__/accounts-flow.test.tsx
git commit -m "feat(accounts): add expiry editing ui"
```

### Task 6: End-To-End Verification And Spec Hygiene

**Files:**
- Modify: `openspec/changes/add-account-expiry-dates/tasks.md`
- Optionally Modify: `openspec/changes/add-account-expiry-dates/specs/account-expiry/spec.md`
- Test: existing backend/frontend files above

- [ ] **Step 1: Mark completed OpenSpec tasks as the implementation lands**

```md
## 2. Backend expiry behavior

- [x] 2.1 Add expiry to account schemas, mappers, and repository update paths.
- [x] 2.2 Default expiry to 30 days on add/import when the incoming payload has no expiry, and preserve payload expiry when provided.
- [x] 2.3 Add portable import/export support for expiry round-tripping.
- [x] 2.4 Exclude expired accounts from normal selection/routing without mutating lifecycle `status`.
- [x] 2.5 Add `PATCH /api/accounts/{account_id}/expiry` for set/extend/clear operations.
```

- [ ] **Step 2: Run the backend verification suite**

Run: `pytest tests/integration/test_accounts_api.py tests/integration/test_accounts_api_extended.py tests/integration/test_load_balancer_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run the frontend verification suite**

Run: `pnpm vitest run frontend/src/features/accounts/schemas.test.ts frontend/src/features/accounts/api.test.ts frontend/src/features/accounts/components/account-list.test.tsx frontend/src/features/accounts/components/account-detail.test.tsx frontend/src/features/accounts/components/account-expiry-dialog.test.tsx frontend/src/__integration__/accounts-flow.test.tsx`
Expected: PASS.

- [ ] **Step 4: Run OpenSpec validation**

Run: `openspec validate --specs`
Expected: `Totals: 19 passed, 0 failed` or the current all-green total.

- [ ] **Step 5: Review git diff before final handoff**

Run: `git diff --stat HEAD~5..HEAD`
Expected: only the planned account expiry files plus their tests and OpenSpec task updates.

- [ ] **Step 6: Commit the verification pass**

```bash
git add openspec/changes/add-account-expiry-dates/tasks.md
git commit -m "chore(accounts): verify account expiry implementation"
```

## Self-Review

### Spec coverage

- `accounts carry an independent expiry date` -> Task 1 adds the persisted field, API fields, and manual update endpoint.
- `default expiry to 30 days on add/import` -> Task 2 adds auth/import defaulting and reset-on-reimport behavior.
- `portable import/export preserve expiry` -> Task 2 adds portable parser/export serializer coverage.
- `expired accounts are excluded from normal selection` -> Task 3 applies routing exclusion in shared backend selection paths.
- `operators can manually edit account expiry` -> Tasks 1, 4, and 5 cover API contract, frontend mutation, and UI/editor flow.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Every code-changing step includes a concrete code block.
- Every verification step includes a concrete command and expected result.

### Type consistency

- Backend response names stay aligned with current aliasing: `expires_at` in Python models, `expiresAt` / `isExpired` on API payloads.
- Frontend mutation payload matches the backend request alias: `{ expiresAt: string | null }`.
- Routing logic uses the persisted `Account.expires_at` field rather than inventing a second runtime-only expiry source.
