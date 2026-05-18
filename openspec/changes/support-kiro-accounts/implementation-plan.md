# Kiro Account Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class Kiro accounts to codex-lb's existing account pool, labeled by provider, with Kiro-backed generation mapped to `claude-sonnet-4.6`.

**Architecture:** Store `openai` and `kiro` as account provider values on the existing `accounts` table, keeping one shared load-balancer pool. Account selection stays centralized; after selection, `ProxyService` dispatches to either the existing ChatGPT/Codex adapter or a new Kiro adapter that refreshes Kiro credentials, translates internal Responses requests to Kiro payloads, parses Kiro event streams, and emits existing OpenAI-compatible output. Chat Completions continues to map through Responses before provider dispatch.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, aiohttp, pytest, React, Zod, TanStack Query, Vitest, React Testing Library

**Plan Location Note:** The writing-plans default path is `docs/superpowers/plans`, but this repository's AGENTS instructions make OpenSpec the SSOT and forbid feature behavior docs under `docs/`. This plan lives under `openspec/changes/support-kiro-accounts/implementation-plan.md`.

---

### Task 1: Add Provider-Aware Account Storage

**Files:**
- Create: `app/db/alembic/versions/20260516_000000_add_kiro_account_provider_fields.py`
- Modify: `app/db/models.py`
- Modify: `app/modules/accounts/schemas.py`
- Modify: `app/modules/accounts/mappers.py`
- Modify: `frontend/src/features/accounts/schemas.ts`
- Modify: `frontend/src/test/mocks/factories.ts` if account factory requires new fields
- Test: `tests/integration/test_db_models.py`
- Test: `tests/integration/test_accounts_api.py`
- Test: `frontend/src/features/accounts/schemas.test.ts`

- [ ] **Step 1: Write failing backend schema tests**

Add these tests near existing account model/API coverage.

```python
# tests/integration/test_db_models.py
async def test_account_provider_defaults_to_openai(async_session):
    encryptor = TokenEncryptor()
    account = Account(
        id="acc_provider_default",
        chatgpt_account_id="raw_provider_default",
        email="provider-default@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=utcnow(),
        status=AccountStatus.ACTIVE,
    )
    async_session.add(account)
    await async_session.commit()

    stored = await async_session.get(Account, "acc_provider_default")

    assert stored.provider == AccountProvider.OPENAI
    assert stored.kiro_auth_method is None
    assert stored.kiro_profile_arn is None


# tests/integration/test_accounts_api.py
async def test_list_accounts_includes_openai_provider(async_client):
    auth_json = _make_auth_json("acc_provider_list", "provider-list@example.com")
    await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("auth.json", json.dumps(auth_json), "application/json")},
    )

    response = await async_client.get("/api/accounts")

    assert response.status_code == 200
    row = next(item for item in response.json()["accounts"] if item["email"] == "provider-list@example.com")
    assert row["provider"] == "openai"
```

- [ ] **Step 2: Write failing frontend schema test**

```typescript
// frontend/src/features/accounts/schemas.test.ts
it("parses account provider labels", () => {
  const parsed = AccountSummarySchema.parse({
    accountId: "acc_provider",
    email: "provider@example.com",
    displayName: "provider@example.com",
    planType: "plus",
    status: "active",
    provider: "kiro",
  });

  expect(parsed.provider).toBe("kiro");
});
```

- [ ] **Step 3: Run failing tests**

Run:

```bash
uv run python -m pytest tests/integration/test_db_models.py::test_account_provider_defaults_to_openai tests/integration/test_accounts_api.py::test_list_accounts_includes_openai_provider -q
cd frontend && bun test src/features/accounts/schemas.test.ts
```

Expected: backend fails because provider fields do not exist; frontend fails because `provider` is not in `AccountSummarySchema`.

- [ ] **Step 4: Add ORM enum and columns**

```python
# app/db/models.py
class AccountProvider(str, Enum):
    OPENAI = "openai"
    KIRO = "kiro"


class Account(Base):
    __tablename__ = "accounts"

    provider: Mapped[AccountProvider] = mapped_column(
        SqlEnum(
            AccountProvider,
            name="account_provider",
            validate_strings=True,
            values_callable=_enum_values,
        ),
        default=AccountProvider.OPENAI,
        server_default=text("'openai'"),
        nullable=False,
    )
    kiro_auth_method: Mapped[str | None] = mapped_column(String, nullable=True)
    kiro_client_id_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    kiro_client_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    kiro_region: Mapped[str | None] = mapped_column(String, nullable=True)
    kiro_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kiro_machine_id: Mapped[str | None] = mapped_column(String, nullable=True)
    kiro_profile_arn: Mapped[str | None] = mapped_column(String, nullable=True)
    kiro_provider: Mapped[str | None] = mapped_column(String, nullable=True)
```

If the existing `id_token_encrypted` column remains non-nullable in this task, Kiro import in Task 2 stores an encrypted empty string there. If implementation changes it to nullable, include that in the migration and update mappers that read token health.

- [ ] **Step 5: Add Alembic migration**

Use `uv run alembic heads` to confirm the current head. If `20260512_000000_add_accounts_routing_tier` is still the only head, use this revision shape.

```python
# app/db/alembic/versions/20260516_000000_add_kiro_account_provider_fields.py
"""add kiro account provider fields

Revision ID: 20260516_000000_add_kiro_account_provider_fields
Revises: 20260512_000000_add_accounts_routing_tier
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260516_000000_add_kiro_account_provider_fields"
down_revision = "20260512_000000_add_accounts_routing_tier"
branch_labels = None
depends_on = None


def _columns(bind: sa.engine.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        if "provider" not in columns:
            batch_op.add_column(sa.Column("provider", sa.String(), nullable=False, server_default="openai"))
        if "kiro_auth_method" not in columns:
            batch_op.add_column(sa.Column("kiro_auth_method", sa.String(), nullable=True))
        if "kiro_client_id_encrypted" not in columns:
            batch_op.add_column(sa.Column("kiro_client_id_encrypted", sa.LargeBinary(), nullable=True))
        if "kiro_client_secret_encrypted" not in columns:
            batch_op.add_column(sa.Column("kiro_client_secret_encrypted", sa.LargeBinary(), nullable=True))
        if "kiro_region" not in columns:
            batch_op.add_column(sa.Column("kiro_region", sa.String(), nullable=True))
        if "kiro_expires_at" not in columns:
            batch_op.add_column(sa.Column("kiro_expires_at", sa.Integer(), nullable=True))
        if "kiro_machine_id" not in columns:
            batch_op.add_column(sa.Column("kiro_machine_id", sa.String(), nullable=True))
        if "kiro_profile_arn" not in columns:
            batch_op.add_column(sa.Column("kiro_profile_arn", sa.String(), nullable=True))
        if "kiro_provider" not in columns:
            batch_op.add_column(sa.Column("kiro_provider", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE accounts SET provider = 'openai' WHERE provider IS NULL OR provider = ''"))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        for column in (
            "kiro_provider",
            "kiro_profile_arn",
            "kiro_machine_id",
            "kiro_expires_at",
            "kiro_region",
            "kiro_client_secret_encrypted",
            "kiro_client_id_encrypted",
            "kiro_auth_method",
            "provider",
        ):
            if column in columns:
                batch_op.drop_column(column)
```

- [ ] **Step 6: Expose provider in backend and frontend schemas**

```python
# app/modules/accounts/schemas.py
AccountProviderValue = Literal["openai", "kiro"]


class AccountSummary(DashboardModel):
    account_id: str
    provider: AccountProviderValue = "openai"
```

```python
# app/modules/accounts/mappers.py
def _account_provider(account: Account) -> AccountProviderValue:
    value = getattr(account.provider, "value", account.provider)
    return "kiro" if value == "kiro" else "openai"


return AccountSummary(
    account_id=account.id,
    provider=_account_provider(account),
    ...
)
```

```typescript
// frontend/src/features/accounts/schemas.ts
export const AccountProviderSchema = z.enum(["openai", "kiro"]);

export const AccountSummarySchema = z.object({
  accountId: z.string(),
  provider: AccountProviderSchema.default("openai"),
});
```

- [ ] **Step 7: Run storage/schema tests and commit**

Run:

```bash
uv run python -m pytest tests/integration/test_db_models.py::test_account_provider_defaults_to_openai tests/integration/test_accounts_api.py::test_list_accounts_includes_openai_provider -q
cd frontend && bun test src/features/accounts/schemas.test.ts
```

Expected: all listed tests pass.

Commit:

```bash
git add app/db/models.py app/db/alembic/versions/20260516_000000_add_kiro_account_provider_fields.py app/modules/accounts/schemas.py app/modules/accounts/mappers.py frontend/src/features/accounts/schemas.ts tests/integration/test_db_models.py tests/integration/test_accounts_api.py frontend/src/features/accounts/schemas.test.ts
git commit -m "feat: add account provider storage"
```

### Task 2: Add Kiro Account Import And Token Refresh

**Files:**
- Create: `app/modules/accounts/kiro_auth.py`
- Modify: `app/modules/accounts/portable.py`
- Modify: `app/modules/accounts/service.py`
- Modify: `app/modules/accounts/schemas.py`
- Modify: `app/modules/accounts/api.py`
- Test: `tests/unit/test_kiro_auth.py`
- Test: `tests/integration/test_accounts_api.py`

- [ ] **Step 1: Write failing Kiro import and refresh tests**

```python
# tests/integration/test_accounts_api.py
async def test_import_kiro_account_persists_provider_fields(async_client):
    payload = {
        "provider": "kiro",
        "email": "kiro@example.com",
        "accessToken": "kiro-access",
        "refreshToken": "kiro-refresh",
        "authMethod": "idc",
        "clientId": "client-id",
        "clientSecret": "client-secret",
        "region": "us-east-1",
        "expiresAt": 1790000000,
        "machineId": "machine-123",
        "profileArn": "arn:aws:codewhisperer:us-east-1:123:profile/test",
    }

    response = await async_client.post(
        "/api/accounts/import",
        files={"auth_json": ("kiro.json", json.dumps(payload), "application/json")},
    )

    assert response.status_code == 200
    assert response.json()["accounts"][0]["provider"] == "kiro"
    listing = await async_client.get("/api/accounts")
    row = next(item for item in listing.json()["accounts"] if item["email"] == "kiro@example.com")
    assert row["provider"] == "kiro"


# tests/unit/test_kiro_auth.py
async def test_refresh_kiro_oidc_token_posts_to_region_oidc(aiohttp_server):
    seen = {}

    async def handler(request):
        seen["payload"] = await request.json()
        return web.json_response(
            {
                "accessToken": "new-access",
                "refreshToken": "new-refresh",
                "expiresIn": 3600,
                "profileArn": "arn:new",
            }
        )

    app = web.Application()
    app.router.add_post("/token", handler)
    server = await aiohttp_server(app)

    result = await refresh_kiro_token(
        KiroRefreshInput(
            auth_method="idc",
            refresh_token="old-refresh",
            client_id="client-id",
            client_secret="client-secret",
            region="us-east-1",
            social_refresh_base_url=None,
            oidc_base_url=str(server.make_url("")),
        )
    )

    assert result.access_token == "new-access"
    assert result.refresh_token == "new-refresh"
    assert result.profile_arn == "arn:new"
    assert seen["payload"]["grantType"] == "refresh_token"
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run python -m pytest tests/integration/test_accounts_api.py::test_import_kiro_account_persists_provider_fields tests/unit/test_kiro_auth.py -q
```

Expected: fails because Kiro import and `kiro_auth` module do not exist.

- [ ] **Step 3: Add Kiro refresh module**

```python
# app/modules/accounts/kiro_auth.py
from __future__ import annotations

from dataclasses import dataclass
from time import time

import aiohttp


@dataclass(frozen=True)
class KiroRefreshInput:
    auth_method: str
    refresh_token: str
    client_id: str | None = None
    client_secret: str | None = None
    region: str | None = None
    social_refresh_base_url: str | None = None
    oidc_base_url: str | None = None


@dataclass(frozen=True)
class KiroRefreshResult:
    access_token: str
    refresh_token: str
    expires_at: int
    profile_arn: str | None = None


class KiroRefreshError(Exception):
    def __init__(self, message: str, *, permanent: bool = False) -> None:
        super().__init__(message)
        self.permanent = permanent


async def refresh_kiro_token(data: KiroRefreshInput) -> KiroRefreshResult:
    auth_method = data.auth_method.lower().strip()
    if auth_method == "social":
        url = f"{(data.social_refresh_base_url or 'https://prod.us-east-1.auth.desktop.kiro.dev').rstrip('/')}/refreshToken"
        payload = {"refreshToken": data.refresh_token}
    else:
        if not data.client_id or not data.client_secret:
            raise KiroRefreshError("Kiro OIDC refresh requires client id and client secret", permanent=True)
        region = data.region or "us-east-1"
        base = (data.oidc_base_url or f"https://oidc.{region}.amazonaws.com").rstrip("/")
        url = f"{base}/token"
        payload = {
            "clientId": data.client_id,
            "clientSecret": data.client_secret,
            "refreshToken": data.refresh_token,
            "grantType": "refresh_token",
        }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            body = await response.json(content_type=None)
            if response.status >= 400:
                raise KiroRefreshError(f"Kiro refresh failed: HTTP {response.status}", permanent=response.status in {400, 401, 403})
    access_token = str(body.get("accessToken") or "")
    refresh_token = str(body.get("refreshToken") or data.refresh_token)
    expires_in = int(body.get("expiresIn") or 0)
    if not access_token or expires_in <= 0:
        raise KiroRefreshError("Kiro refresh response missing access token or expiry", permanent=False)
    return KiroRefreshResult(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=int(time()) + expires_in,
        profile_arn=str(body["profileArn"]) if body.get("profileArn") else None,
    )
```

- [ ] **Step 4: Extend portable import normalization**

Add a provider-aware normalized record.

```python
# app/modules/accounts/portable.py
class PortableAccountProvider(str, Enum):
    OPENAI = "openai"
    KIRO = "kiro"


class PortableAccountRecord(BaseModel):
    provider: PortableAccountProvider = PortableAccountProvider.OPENAI
    email: str
    plan_type: str
    raw_account_id: str | None = None
    id_token: str = ""
    access_token: str
    refresh_token: str
    kiro_auth_method: str | None = None
    kiro_client_id: str | None = None
    kiro_client_secret: str | None = None
    kiro_region: str | None = None
    kiro_expires_at: int | None = None
    kiro_machine_id: str | None = None
    kiro_profile_arn: str | None = None
    kiro_provider: str | None = None


class KiroAccountImport(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    provider: Literal["kiro"]
    email: str = DEFAULT_EMAIL
    access_token: str = Field(validation_alias=AliasChoices("access_token", "accessToken"))
    refresh_token: str = Field(validation_alias=AliasChoices("refresh_token", "refreshToken"))
    auth_method: str = Field(validation_alias=AliasChoices("auth_method", "authMethod"))
    client_id: str | None = Field(default=None, validation_alias=AliasChoices("client_id", "clientId"))
    client_secret: str | None = Field(default=None, validation_alias=AliasChoices("client_secret", "clientSecret"))
    region: str | None = "us-east-1"
    expires_at: int | None = Field(default=None, validation_alias=AliasChoices("expires_at", "expiresAt"))
    machine_id: str | None = Field(default=None, validation_alias=AliasChoices("machine_id", "machineId"))
    profile_arn: str | None = Field(default=None, validation_alias=AliasChoices("profile_arn", "profileArn"))
    kiro_provider: str | None = Field(default=None, validation_alias=AliasChoices("kiro_provider", "kiroProvider"))


def parse_portable_account_batch(raw: bytes) -> PortableAccountBatch:
    data = json.loads(raw)
    if isinstance(data, dict) and data.get("provider") == "kiro":
        account = KiroAccountImport.model_validate(data)
        return PortableAccountBatch(
            format=PortableImportFormat.AUTH_JSON,
            accounts=[
                PortableAccountRecord(
                    provider=PortableAccountProvider.KIRO,
                    email=account.email,
                    plan_type="kiro",
                    raw_account_id=None,
                    id_token="",
                    access_token=account.access_token,
                    refresh_token=account.refresh_token,
                    kiro_auth_method=account.auth_method,
                    kiro_client_id=account.client_id,
                    kiro_client_secret=account.client_secret,
                    kiro_region=account.region or "us-east-1",
                    kiro_expires_at=account.expires_at,
                    kiro_machine_id=account.machine_id,
                    kiro_profile_arn=account.profile_arn,
                    kiro_provider=account.kiro_provider,
                )
            ],
        )
```

- [ ] **Step 5: Persist provider-specific account fields**

```python
# app/modules/accounts/service.py
account = Account(
    id=account_id,
    provider=AccountProvider.KIRO if portable_account.provider.value == "kiro" else AccountProvider.OPENAI,
    chatgpt_account_id=raw_account_id,
    email=email,
    plan_type=portable_account.plan_type,
    access_token_encrypted=self._encryptor.encrypt(portable_account.access_token),
    refresh_token_encrypted=self._encryptor.encrypt(portable_account.refresh_token),
    id_token_encrypted=self._encryptor.encrypt(portable_account.id_token or ""),
    last_refresh=portable_account.last_refresh_at or utcnow(),
    status=AccountStatus.ACTIVE,
    deactivation_reason=None,
    kiro_auth_method=portable_account.kiro_auth_method,
    kiro_client_id_encrypted=self._encryptor.encrypt(portable_account.kiro_client_id) if portable_account.kiro_client_id else None,
    kiro_client_secret_encrypted=self._encryptor.encrypt(portable_account.kiro_client_secret) if portable_account.kiro_client_secret else None,
    kiro_region=portable_account.kiro_region,
    kiro_expires_at=portable_account.kiro_expires_at,
    kiro_machine_id=portable_account.kiro_machine_id,
    kiro_profile_arn=portable_account.kiro_profile_arn,
    kiro_provider=portable_account.kiro_provider,
)
```

For Kiro account IDs, generate a stable local ID from email plus provider, for example `kiro_<sha256(email)[:12]>`, instead of using ChatGPT account claims.

- [ ] **Step 6: Run import/refresh tests and commit**

Run:

```bash
uv run python -m pytest tests/integration/test_accounts_api.py::test_import_kiro_account_persists_provider_fields tests/unit/test_kiro_auth.py -q
```

Expected: tests pass.

Commit:

```bash
git add app/modules/accounts/kiro_auth.py app/modules/accounts/portable.py app/modules/accounts/service.py app/modules/accounts/schemas.py app/modules/accounts/api.py tests/unit/test_kiro_auth.py tests/integration/test_accounts_api.py
git commit -m "feat: import and refresh kiro accounts"
```

### Task 3: Add Kiro Upstream Client And Event Parser

**Files:**
- Create: `app/core/clients/kiro.py`
- Test: `tests/unit/test_kiro_client.py`

- [ ] **Step 1: Write failing event parser and header tests**

```python
# tests/unit/test_kiro_client.py
def test_build_kiro_headers_include_bearer_and_machine_id():
    headers = build_kiro_headers(
        access_token="access",
        host="q.us-east-1.amazonaws.com",
        machine_id="machine-123",
        api_name="codewhispererstreaming",
        sdk_version="1.0.34",
        mode="m/E",
        kiro_version="0.11.107",
        system_version="Darwin",
        node_version="22.0.0",
    )

    assert headers["Authorization"] == "Bearer access"
    assert "KiroIDE-0.11.107-machine-123" in headers["User-Agent"]
    assert headers["x-amzn-codewhisperer-optout"] == "true"


def test_parse_kiro_json_event_text_delta():
    events = list(parse_kiro_json_event({"type": "assistantResponseEvent", "content": "hi"}))

    assert events == [KiroStreamEvent(type="text", text="hi")]
```

- [ ] **Step 2: Run failing client tests**

Run:

```bash
uv run python -m pytest tests/unit/test_kiro_client.py -q
```

Expected: module import fails.

- [ ] **Step 3: Add Kiro client interfaces**

```python
# app/core/clients/kiro.py
from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any

import aiohttp

from app.core.types import JsonValue

KIRO_MODEL = "claude-sonnet-4.6"


@dataclass(frozen=True)
class KiroAccountCredentials:
    account_id: str
    access_token: str
    machine_id: str | None = None
    profile_arn: str | None = None


@dataclass(frozen=True)
class KiroStreamEvent:
    type: str
    text: str | None = None
    is_thinking: bool = False
    tool_use: dict[str, JsonValue] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    credits: float | None = None
    error: str | None = None


class KiroUpstreamError(Exception):
    def __init__(self, message: str, *, status: int | None = None, code: str = "upstream_error") -> None:
        super().__init__(message)
        self.status = status
        self.code = code
```

Add these functions:

```python
def build_kiro_headers(... ) -> dict[str, str]: ...
def parse_kiro_json_event(event: Mapping[str, Any]) -> list[KiroStreamEvent]: ...
async def stream_kiro_generation(payload: Mapping[str, JsonValue], credentials: KiroAccountCredentials, *, session: aiohttp.ClientSession | None = None) -> AsyncIterator[KiroStreamEvent]: ...
```

`stream_kiro_generation()` can initially accept newline-delimited JSON in tests and have a separate private `_iter_aws_event_stream_bytes()` for real AWS frames. Keep frame parsing isolated so tests can cover it without real Kiro network calls.

- [ ] **Step 4: Implement AWS event-stream parsing**

Add private helpers in `app/core/clients/kiro.py`.

```python
def _parse_aws_event_stream_message(buffer: bytes) -> tuple[dict[str, str], bytes]:
    total_length = int.from_bytes(buffer[0:4], "big")
    headers_length = int.from_bytes(buffer[4:8], "big")
    headers_blob = buffer[12 : 12 + headers_length]
    payload = buffer[12 + headers_length : total_length - 4]
    return _parse_event_headers(headers_blob), payload
```

Tests should build one `assistantResponseEvent` frame and assert a text `KiroStreamEvent`.

- [ ] **Step 5: Run client tests and commit**

Run:

```bash
uv run python -m pytest tests/unit/test_kiro_client.py -q
```

Expected: tests pass.

Commit:

```bash
git add app/core/clients/kiro.py tests/unit/test_kiro_client.py
git commit -m "feat: add kiro upstream client"
```

### Task 4: Add Responses-To-Kiro Translator

**Files:**
- Create: `app/core/kiro/translator.py`
- Create: `app/core/kiro/__init__.py`
- Test: `tests/unit/test_kiro_translator.py`

- [ ] **Step 1: Write failing translator tests**

```python
# tests/unit/test_kiro_translator.py
def test_responses_text_forces_claude_sonnet_46():
    req = ResponsesRequest.model_validate({"model": "gpt-5.5", "input": "hello", "instructions": "be brief"})

    payload = responses_to_kiro_payload(req)

    current = payload["conversationState"]["currentMessage"]["userInputMessage"]
    assert current["modelId"] == "claude-sonnet-4.6"
    assert "be brief" in current["content"]
    assert "hello" in current["content"]


def test_responses_tool_result_maps_to_kiro_context():
    req = ResponsesRequest.model_validate(
        {
            "model": "gpt-5.5",
            "input": [{"type": "function_call_output", "call_id": "call_1", "output": "done"}],
        }
    )

    payload = responses_to_kiro_payload(req)

    context = payload["conversationState"]["currentMessage"]["userInputMessage"]["userInputMessageContext"]
    assert context["toolResults"][0]["toolUseId"] == "call_1"
    assert context["toolResults"][0]["content"][0]["text"] == "done"
```

- [ ] **Step 2: Run failing translator tests**

Run:

```bash
uv run python -m pytest tests/unit/test_kiro_translator.py -q
```

Expected: module import fails.

- [ ] **Step 3: Add translator module**

```python
# app/core/kiro/translator.py
from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

from app.core.clients.kiro import KIRO_MODEL
from app.core.openai.requests import ResponsesRequest
from app.core.types import JsonObject, JsonValue

THINKING_MODE_PROMPT = "<thinking_mode>enabled</thinking_mode>\n<max_thinking_length>200000</max_thinking_length>"
MINIMAL_FALLBACK_USER_CONTENT = "."


def responses_to_kiro_payload(req: ResponsesRequest) -> JsonObject:
    instructions = (req.instructions or "").strip()
    current_text, images, tool_results, history = _responses_input_to_kiro(req.input, instructions)
    if not current_text and not images and not tool_results:
        current_text = MINIMAL_FALLBACK_USER_CONTENT
    current_message: JsonObject = {
        "content": current_text,
        "modelId": KIRO_MODEL,
        "origin": "AI_EDITOR",
    }
    if images:
        current_message["images"] = images
    tools = _responses_tools_to_kiro(req.tools or [])
    if tools or tool_results:
        current_message["userInputMessageContext"] = {
            "tools": tools,
            "toolResults": tool_results,
        }
    conversation_state: JsonObject = {
        "chatTriggerType": "MANUAL",
        "agentTaskType": "vibe",
        "agentContinuationId": uuid4().hex,
        "conversationId": _conversation_id(req, instructions),
        "currentMessage": {"userInputMessage": current_message},
    }
    if history:
        conversation_state["history"] = history
    payload: JsonObject = {"conversationState": conversation_state}
    if req.max_output_tokens:
        payload["inferenceConfig"] = {"maxTokens": req.max_output_tokens}
    return payload
```

Implement private helpers in the same file:

- `_responses_input_to_kiro(input_value, instructions) -> tuple[str, list[JsonObject], list[JsonObject], list[JsonObject]]`
- `_responses_tools_to_kiro(tools) -> list[JsonObject]`
- `_conversation_id(req, instructions) -> str`
- `_text_from_content(value) -> str`
- `_image_from_part(part) -> JsonObject | None`

Use Kiro-Go behavior as reference: prepend instructions to current content, preserve assistant history where practical, convert `function_call_output` to `toolResults`, and convert supported function/custom tools to Kiro tool specifications.

- [ ] **Step 4: Run translator tests and commit**

Run:

```bash
uv run python -m pytest tests/unit/test_kiro_translator.py -q
```

Expected: tests pass.

Commit:

```bash
git add app/core/kiro/__init__.py app/core/kiro/translator.py tests/unit/test_kiro_translator.py
git commit -m "feat: translate responses to kiro payloads"
```

### Task 5: Dispatch Selected Kiro Accounts Through Kiro Adapter

**Files:**
- Modify: `app/modules/proxy/service.py`
- Modify: `app/modules/proxy/load_balancer.py`
- Modify: `app/modules/proxy/schemas.py`
- Modify: `app/db/models.py`
- Modify: `app/core/openai/models.py` only if response event construction needs a missing type
- Test: `tests/integration/test_proxy_responses.py`
- Test: `tests/integration/test_proxy_chat_completions.py`
- Test: `tests/integration/test_load_balancer_integration.py`

- [ ] **Step 1: Write failing mixed-pool and Kiro proxy tests**

```python
# tests/integration/test_proxy_responses.py
async def test_v1_responses_can_stream_from_kiro_account(async_client, async_session, monkeypatch):
    account = _make_kiro_account("kiro_stream", "kiro-stream@example.com")
    async_session.add(account)
    await async_session.commit()

    seen_payloads = []

    async def fake_stream_kiro_generation(payload, credentials, **_kwargs):
        seen_payloads.append(payload)
        yield KiroStreamEvent(type="text", text="hello")
        yield KiroStreamEvent(type="usage", input_tokens=3, output_tokens=2)

    monkeypatch.setattr("app.modules.proxy.service.stream_kiro_generation", fake_stream_kiro_generation)

    response = await async_client.post("/v1/responses", json={"model": "gpt-5.5", "input": "hi", "stream": True})

    assert response.status_code == 200
    assert "response.output_text.delta" in response.text
    current = seen_payloads[0]["conversationState"]["currentMessage"]["userInputMessage"]
    assert current["modelId"] == "claude-sonnet-4.6"


# tests/integration/test_proxy_chat_completions.py
async def test_chat_completions_can_stream_from_kiro_account(async_client, async_session, monkeypatch):
    async_session.add(_make_kiro_account("kiro_chat", "kiro-chat@example.com"))
    await async_session.commit()

    async def fake_stream_kiro_generation(payload, credentials, **_kwargs):
        yield KiroStreamEvent(type="text", text="hello")

    monkeypatch.setattr("app.modules.proxy.service.stream_kiro_generation", fake_stream_kiro_generation)

    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": "gpt-5.5", "messages": [{"role": "user", "content": "hi"}], "stream": True},
    )

    assert response.status_code == 200
    assert "chat.completion.chunk" in response.text
    assert "data: [DONE]" in response.text
```

- [ ] **Step 2: Run failing proxy tests**

Run:

```bash
uv run python -m pytest tests/integration/test_proxy_responses.py::test_v1_responses_can_stream_from_kiro_account tests/integration/test_proxy_chat_completions.py::test_chat_completions_can_stream_from_kiro_account -q
```

Expected: fails because proxy service has no Kiro dispatch.

- [ ] **Step 3: Add provider helpers in ProxyService**

```python
# app/modules/proxy/service.py
def _account_provider(account: Account) -> str:
    value = getattr(account.provider, "value", account.provider)
    return "kiro" if value == "kiro" else "openai"


def _is_kiro_account(account: Account) -> bool:
    return _account_provider(account) == "kiro"
```

- [ ] **Step 4: Add Kiro credential construction**

```python
# app/modules/proxy/service.py
def _kiro_credentials_for_account(self, account: Account) -> KiroAccountCredentials:
    return KiroAccountCredentials(
        account_id=account.id,
        access_token=self._encryptor.decrypt(account.access_token_encrypted),
        machine_id=account.kiro_machine_id,
        profile_arn=account.kiro_profile_arn,
    )
```

Add `_ensure_kiro_fresh_with_budget(account, timeout_seconds, force=False)` using `refresh_kiro_token()` from Task 2. Update encrypted access/refresh tokens and `kiro_expires_at`; preserve existing singleflight style if practical, but keep the first implementation scoped and covered by concurrency-safe repository update tests.

- [ ] **Step 5: Add Kiro event-to-Responses stream adapter**

```python
# app/modules/proxy/service.py
async def _stream_kiro_responses_attempt(
    self,
    payload: ResponsesRequest,
    account: Account,
    *,
    request_started_at: float,
    api_key: ApiKeyData | None,
    settlement: _StreamSettlement,
) -> AsyncIterator[str]:
    response_id = f"resp_{uuid4().hex}"
    message_id = f"msg_{uuid4().hex}"
    yield format_sse_event({"type": "response.created", "response": {"id": response_id, "status": "in_progress", "model": payload.model}})
    yield format_sse_event({"type": "response.output_item.added", "item_id": message_id, "output_index": 0, "item": {"id": message_id, "type": "message", "status": "in_progress", "role": "assistant"}})
    yield format_sse_event({"type": "response.content_part.added", "item_id": message_id, "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": ""}})
    output_text = ""
    usage_input = 0
    usage_output = 0
    kiro_payload = responses_to_kiro_payload(payload)
    account = await self._ensure_kiro_fresh_with_budget(account, timeout_seconds=max(get_settings().proxy_request_budget_seconds - (time.monotonic() - request_started_at), 1.0))
    async for event in stream_kiro_generation(kiro_payload, self._kiro_credentials_for_account(account)):
        if event.type == "text" and event.text:
            output_text += event.text
            yield format_sse_event({"type": "response.output_text.delta", "item_id": message_id, "output_index": 0, "content_index": 0, "delta": event.text})
        elif event.input_tokens is not None:
            usage_input = event.input_tokens
            usage_output = event.output_tokens or usage_output
    yield format_sse_event({"type": "response.output_text.done", "item_id": message_id, "output_index": 0, "content_index": 0, "text": output_text})
    yield format_sse_event({"type": "response.content_part.done", "item_id": message_id, "output_index": 0, "content_index": 0, "part": {"type": "output_text", "text": output_text}})
    yield format_sse_event({"type": "response.output_item.done", "item_id": message_id, "output_index": 0, "item": {"id": message_id, "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": output_text}]}})
    yield format_sse_event({"type": "response.completed", "response": {"id": response_id, "status": "completed", "model": payload.model, "output": [{"id": message_id, "type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": output_text}]}], "usage": {"input_tokens": usage_input, "output_tokens": usage_output, "total_tokens": usage_input + usage_output}}})
```

Adapt the exact event schema to the existing `OpenAIResponsePayload` parser if tests reveal missing required fields. Keep construction in a helper so HTTP bridge/websocket code can call the same adapter if Kiro websocket support is added.

- [ ] **Step 6: Branch in stream attempts**

In the place where `stream_responses()` currently calls `_stream_responses_attempt()` after selecting and refreshing an account, branch:

```python
if _is_kiro_account(account):
    async for event_block in self._stream_kiro_responses_attempt(
        payload,
        account,
        request_started_at=start,
        api_key=api_key,
        settlement=settlement,
    ):
        yield event_block
else:
    async for event_block in self._stream_responses_attempt(...):
        yield event_block
```

Preserve existing failover and pre-commit retry behavior by treating Kiro errors before first downstream text delta as retryable when their status/code matches quota, auth refresh transient, network, or 5xx categories.

- [ ] **Step 7: Run proxy tests and commit**

Run:

```bash
uv run python -m pytest tests/integration/test_proxy_responses.py::test_v1_responses_can_stream_from_kiro_account tests/integration/test_proxy_chat_completions.py::test_chat_completions_can_stream_from_kiro_account -q
```

Expected: tests pass.

Commit:

```bash
git add app/modules/proxy/service.py app/modules/proxy/load_balancer.py app/modules/proxy/schemas.py tests/integration/test_proxy_responses.py tests/integration/test_proxy_chat_completions.py tests/integration/test_load_balancer_integration.py
git commit -m "feat: dispatch kiro generation requests"
```

### Task 6: Add Provider Eligibility, Compact Behavior, And Observability

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/modules/proxy/service.py`
- Modify: `app/modules/proxy/load_balancer.py`
- Modify: `app/modules/proxy/schemas.py`
- Modify: `app/modules/request_logs/schemas.py` if request log API exposes new fields
- Modify: `frontend/src/features/request-logs/schemas.ts` if frontend exposes request logs
- Test: `tests/integration/test_proxy_transcriptions.py`
- Test: `tests/integration/test_proxy_compact.py`
- Test: `tests/integration/test_request_logs_api.py`

- [ ] **Step 1: Write failing provider eligibility and log tests**

```python
# tests/integration/test_proxy_transcriptions.py
async def test_transcription_does_not_select_kiro_account(async_client, async_session, monkeypatch):
    async_session.add(_make_kiro_account("kiro_transcribe", "kiro-transcribe@example.com"))
    await async_session.commit()

    response = await async_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"RIFF....WAVEfmt ", "audio/wav")},
        data={"model": "gpt-4o-transcribe"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] in {"no_compatible_accounts", "no_accounts"}


# tests/integration/test_proxy_compact.py
async def test_kiro_compact_returns_compatible_response(async_client, async_session, monkeypatch):
    async_session.add(_make_kiro_account("kiro_compact", "kiro-compact@example.com"))
    await async_session.commit()

    response = await async_client.post(
        "/backend-api/codex/responses/compact",
        json={"model": "gpt-5.5", "input": "long context"},
    )

    assert response.status_code == 200
    assert "encrypted_content" not in response.text
```

- [ ] **Step 2: Run failing tests**

Run:

```bash
uv run python -m pytest tests/integration/test_proxy_transcriptions.py::test_transcription_does_not_select_kiro_account tests/integration/test_proxy_compact.py::test_kiro_compact_returns_compatible_response -q
```

Expected: transcription may try Kiro or fail with generic error; compact lacks Kiro behavior.

- [ ] **Step 3: Add provider eligibility filters**

Extend `_select_account_with_budget_compatible()` or `_select_account_with_budget()` with `provider_filter: set[str] | None = None`. For transcription, pass `{"openai"}`. For generation, pass `{"openai", "kiro"}` or omit.

```python
selection = await self._select_account_with_budget_compatible(
    deadline,
    request_id=request_id,
    kind="transcribe",
    api_key=api_key,
    prefer_earlier_reset_accounts=prefer_earlier_reset,
    routing_strategy=routing_strategy,
    model=None,
    provider_filter={"openai"},
)
```

If the load balancer only accepts account IDs, compute eligible provider account IDs from cached account state before calling `select_account()`. Return `no_compatible_accounts` when provider filtering removes all otherwise available accounts.

- [ ] **Step 4: Add Kiro compact behavior**

In `compact_responses()`, when selected provider is Kiro, return a minimal compatible `CompactResponsePayload` using existing compact response model fields. The response must not include `encrypted_content`.

```python
if _is_kiro_account(account):
    return CompactResponsePayload(
        response={"model": payload.model, "input": payload.input, "provider": "kiro", "upstream_model": "claude-sonnet-4.6"},
        usage=None,
    )
```

Adapt field names to the actual `CompactResponsePayload` model in `app/core/openai/models.py`; tests define the contract.

- [ ] **Step 5: Add provider/upstream observability**

Add nullable request log fields:

- `provider`
- `upstream_model`

Migration name:

```text
app/db/alembic/versions/20260516_010000_add_request_log_provider_fields.py
```

Write `provider="kiro"` and `upstream_model="claude-sonnet-4.6"` for Kiro requests; write `provider="openai"` and `upstream_model=None` or existing upstream model for OpenAI requests.

- [ ] **Step 6: Run eligibility/log tests and commit**

Run:

```bash
uv run python -m pytest tests/integration/test_proxy_transcriptions.py::test_transcription_does_not_select_kiro_account tests/integration/test_proxy_compact.py::test_kiro_compact_returns_compatible_response tests/integration/test_request_logs_api.py -q
```

Expected: tests pass.

Commit:

```bash
git add app/db/models.py app/db/alembic/versions/20260516_010000_add_request_log_provider_fields.py app/modules/proxy/service.py app/modules/proxy/load_balancer.py app/modules/proxy/schemas.py tests/integration/test_proxy_transcriptions.py tests/integration/test_proxy_compact.py tests/integration/test_request_logs_api.py
git commit -m "feat: add provider-aware proxy eligibility"
```

### Task 7: Add Dashboard Provider Labels And Kiro Import UI

**Files:**
- Modify: `frontend/src/features/accounts/api.ts`
- Modify: `frontend/src/features/accounts/schemas.ts`
- Modify: `frontend/src/features/accounts/components/account-list-item.tsx`
- Modify: `frontend/src/features/accounts/components/account-detail.tsx`
- Modify: `frontend/src/features/accounts/components/import-dialog.tsx`
- Modify: `frontend/src/features/accounts/components/import-dialog.test.tsx`
- Modify: `frontend/src/features/accounts/components/account-list-item.test.tsx`
- Test: `frontend/src/features/accounts/api.test.ts`
- Test: `frontend/src/features/accounts/schemas.test.ts`

- [ ] **Step 1: Write failing frontend UI tests**

```typescript
// frontend/src/features/accounts/components/account-list-item.test.tsx
it("shows kiro provider label", () => {
  const account = createAccountSummary({ provider: "kiro", email: "kiro@example.com" });

  render(<AccountListItem account={account} selected={false} onSelect={() => undefined} />);

  expect(screen.getByText("Kiro")).toBeInTheDocument();
});


// frontend/src/features/accounts/components/import-dialog.test.tsx
it("submits kiro provider import payload", async () => {
  const user = userEvent.setup();
  const onImport = vi.fn().mockResolvedValue(undefined);
  render(<ImportDialog open onOpenChange={() => undefined} onImport={onImport} />);

  await user.click(screen.getByRole("tab", { name: /kiro/i }));
  await user.type(screen.getByLabelText(/email/i), "kiro@example.com");
  await user.type(screen.getByLabelText(/access token/i), "access");
  await user.type(screen.getByLabelText(/refresh token/i), "refresh");
  await user.type(screen.getByLabelText(/client id/i), "client-id");
  await user.type(screen.getByLabelText(/client secret/i), "client-secret");
  await user.click(screen.getByRole("button", { name: /import/i }));

  expect(onImport).toHaveBeenCalledWith(expect.objectContaining({ provider: "kiro" }));
});
```

- [ ] **Step 2: Run failing frontend tests**

Run:

```bash
cd frontend && bun test src/features/accounts/components/account-list-item.test.tsx src/features/accounts/components/import-dialog.test.tsx
```

Expected: provider label and Kiro import controls missing.

- [ ] **Step 3: Add provider label to list/detail**

Use existing badge/chip styling in account components.

```tsx
// frontend/src/features/accounts/components/account-list-item.tsx
const providerLabel = account.provider === "kiro" ? "Kiro" : "OpenAI";

<span className="rounded border px-1.5 py-0.5 text-xs text-muted-foreground">
  {providerLabel}
</span>
```

- [ ] **Step 4: Add Kiro import mode**

Extend `ImportDialog` with a compact tab or segmented control for `OpenAI auth.json` and `Kiro`. Kiro form submits JSON as a file/blob through the existing import endpoint to avoid adding a second frontend API call.

```typescript
const payload = {
  provider: "kiro",
  email,
  accessToken,
  refreshToken,
  authMethod,
  clientId,
  clientSecret,
  region,
  expiresAt: expiresAt ? Math.floor(new Date(expiresAt).getTime() / 1000) : undefined,
  machineId,
  profileArn,
};
const file = new File([JSON.stringify(payload)], "kiro-account.json", { type: "application/json" });
await onImport(file);
```

If the current `onImport` type only accepts `File`, keep it that way. If tests prefer direct payloads, update `importAccount()` to accept `File | KiroImportPayload` and convert payloads inside `api.ts`.

- [ ] **Step 5: Run frontend tests and commit**

Run:

```bash
cd frontend && bun test src/features/accounts/schemas.test.ts src/features/accounts/components/account-list-item.test.tsx src/features/accounts/components/import-dialog.test.tsx src/features/accounts/api.test.ts
```

Expected: tests pass.

Commit:

```bash
git add frontend/src/features/accounts/api.ts frontend/src/features/accounts/schemas.ts frontend/src/features/accounts/components/account-list-item.tsx frontend/src/features/accounts/components/account-detail.tsx frontend/src/features/accounts/components/import-dialog.tsx frontend/src/features/accounts/components/import-dialog.test.tsx frontend/src/features/accounts/components/account-list-item.test.tsx frontend/src/features/accounts/api.test.ts frontend/src/features/accounts/schemas.test.ts
git commit -m "feat: add kiro account dashboard import"
```

### Task 8: Full Verification And OpenSpec Sync

**Files:**
- Modify: `openspec/changes/support-kiro-accounts/tasks.md`
- Modify: `openspec/changes/support-kiro-accounts/context.md` if implementation decisions changed
- Modify: `openspec/changes/support-kiro-accounts/specs/*/spec.md` only if implementation revealed a contract correction

- [ ] **Step 1: Run backend focused tests**

Run:

```bash
uv run python -m pytest \
  tests/unit/test_kiro_auth.py \
  tests/unit/test_kiro_client.py \
  tests/unit/test_kiro_translator.py \
  tests/integration/test_accounts_api.py \
  tests/integration/test_proxy_responses.py \
  tests/integration/test_proxy_chat_completions.py \
  tests/integration/test_proxy_transcriptions.py \
  tests/integration/test_proxy_compact.py \
  tests/integration/test_request_logs_api.py \
  tests/integration/test_load_balancer_integration.py \
  -q
```

Expected: all focused backend tests pass.

- [ ] **Step 2: Run frontend focused tests**

Run:

```bash
cd frontend && bun test \
  src/features/accounts/schemas.test.ts \
  src/features/accounts/api.test.ts \
  src/features/accounts/components/account-list-item.test.tsx \
  src/features/accounts/components/import-dialog.test.tsx
```

Expected: all focused frontend tests pass.

- [ ] **Step 3: Run quality gates**

Run:

```bash
uv run ruff check app tests
uv run ty check
cd frontend && bun run typecheck
openspec validate support-kiro-accounts --strict
openspec validate --specs
```

Expected: all commands pass. If `ty check` reports pre-existing issues unrelated to Kiro work, capture exact files and rerun the most specific `ty` command available for changed backend files.

- [ ] **Step 4: Mark OpenSpec tasks complete**

Update `openspec/changes/support-kiro-accounts/tasks.md` by changing completed task checkboxes from `[ ]` to `[x]` only for implemented and verified work. Do not mark a task complete based on intent alone.

- [ ] **Step 5: Commit verification artifacts**

Commit only OpenSpec updates from this task.

```bash
git add openspec/changes/support-kiro-accounts/tasks.md openspec/changes/support-kiro-accounts/context.md openspec/changes/support-kiro-accounts/specs
git commit -m "docs: mark kiro account support tasks verified"
```

### Task 9: Manual Smoke Check

**Files:**
- No code files required.

- [ ] **Step 1: Start backend and frontend only after focused tests pass**

Run backend:

```bash
uv run codex-lb --host 127.0.0.1 --port 8080
```

Run frontend in another terminal:

```bash
cd frontend && bun run dev --host 127.0.0.1
```

Expected: backend starts on `http://127.0.0.1:8080`; frontend starts on a Vite URL.

- [ ] **Step 2: Add one Kiro account through dashboard**

Use the Accounts import dialog Kiro mode. Confirm account row shows provider label `Kiro`.

- [ ] **Step 3: Send one chat request**

Run:

```bash
curl -N http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-5.5","messages":[{"role":"user","content":"Say pong"}],"stream":true}'
```

Expected: SSE stream returns `chat.completion.chunk` events and ends with `data: [DONE]`. Request logs show provider `kiro` and upstream model `claude-sonnet-4.6`.

- [ ] **Step 4: Stop dev servers and record smoke result**

Stop servers with Ctrl-C. If smoke succeeds, add one short note to `openspec/changes/support-kiro-accounts/context.md` under an "Implementation Notes" section:

```markdown
## Implementation Notes

- Manual smoke confirmed `/v1/chat/completions` can stream through a Kiro account and records upstream model `claude-sonnet-4.6`.
```

Commit:

```bash
git add openspec/changes/support-kiro-accounts/context.md
git commit -m "docs: record kiro support smoke result"
```
