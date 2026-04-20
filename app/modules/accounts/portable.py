from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from app.core.auth import DEFAULT_EMAIL, DEFAULT_PLAN, AuthFile, AuthTokens, claims_from_auth, extract_id_token_claims
from app.core.plan_types import coerce_account_plan_type


class PortableImportFormat(str, Enum):
    AUTH_JSON = "auth_json"
    PORTABLE_JSON = "portable_json"


class PortableAccountRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str | None = None
    email: str
    plan_type: str
    raw_account_id: str | None = None
    id_token: str
    access_token: str
    refresh_token: str
    last_refresh_at: datetime | None = None
    created_at: datetime | None = None


class PortableAccountBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: PortableImportFormat
    accounts: list[PortableAccountRecord]


class PortableExternalTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id_token: str
    access_token: str
    refresh_token: str


class PortableExternalAccountImport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    email: str | None = None
    plan_type: str | None = None
    account_id: str | None = None
    tokens: PortableExternalTokens
    usage_updated_at: int | None = None
    created_at: int | None = None
    last_used: int | None = None


class PortableExternalAccountExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    auth_mode: str = "oauth"
    api_provider_mode: str = "openai_builtin"
    user_id: str | None = None
    plan_type: str
    account_id: str | None = None
    organization_id: str | None = None
    account_structure: str | None = None
    tokens: PortableExternalTokens
    quota: None = None
    usage_updated_at: int | None = None
    tags: list[str] | None = None
    created_at: int | None = None
    last_used: int | None = None


_PORTABLE_EXTERNAL_IMPORTS = TypeAdapter(list[PortableExternalAccountImport])


def parse_portable_account_batch(raw: bytes) -> PortableAccountBatch:
    data = json.loads(raw)
    if isinstance(data, dict):
        auth = AuthFile.model_validate(data)
        return PortableAccountBatch(
            format=PortableImportFormat.AUTH_JSON,
            accounts=[portable_record_from_auth_file(auth)],
        )
    if isinstance(data, list):
        portable_accounts = _PORTABLE_EXTERNAL_IMPORTS.validate_python(data)
        return PortableAccountBatch(
            format=PortableImportFormat.PORTABLE_JSON,
            accounts=[portable_record_from_external_account(account) for account in portable_accounts],
        )
    raise TypeError("Unsupported account import payload")


def portable_record_from_auth_file(auth: AuthFile) -> PortableAccountRecord:
    claims = claims_from_auth(auth)
    return PortableAccountRecord(
        email=claims.email or DEFAULT_EMAIL,
        plan_type=coerce_account_plan_type(claims.plan_type, DEFAULT_PLAN),
        raw_account_id=claims.account_id,
        id_token=auth.tokens.id_token,
        access_token=auth.tokens.access_token,
        refresh_token=auth.tokens.refresh_token,
        last_refresh_at=_to_utc_naive(auth.last_refresh_at),
    )


def portable_record_from_external_account(account: PortableExternalAccountImport) -> PortableAccountRecord:
    auth = AuthFile(
        tokens=AuthTokens(
            id_token=account.tokens.id_token,
            access_token=account.tokens.access_token,
            refresh_token=account.tokens.refresh_token,
            account_id=account.account_id,
        ),
        last_refresh_at=_best_external_timestamp(account),
    )
    claims = claims_from_auth(auth)
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
    )


def build_portable_export_account(
    *,
    stored_account_id: str,
    email: str,
    plan_type: str,
    raw_account_id: str | None,
    id_token: str,
    access_token: str,
    refresh_token: str,
    created_at: datetime | None,
    last_refresh_at: datetime | None,
) -> PortableExternalAccountExport:
    claims = extract_id_token_claims(id_token)
    auth_claims = claims.auth
    user_id = auth_claims.user_id if auth_claims and auth_claims.user_id else claims.sub
    return PortableExternalAccountExport(
        id=stored_account_id,
        email=email,
        user_id=user_id,
        plan_type=plan_type,
        account_id=raw_account_id,
        tokens=PortableExternalTokens(
            id_token=id_token,
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        usage_updated_at=_datetime_to_epoch(last_refresh_at),
        created_at=_datetime_to_epoch(created_at),
    )


def _best_external_timestamp(account: PortableExternalAccountImport) -> datetime | None:
    for epoch_value in (account.usage_updated_at, account.last_used, account.created_at):
        timestamp = _epoch_to_utc_naive(epoch_value)
        if timestamp is not None:
            return timestamp
    return None


def _epoch_to_utc_naive(epoch_value: int | None) -> datetime | None:
    if epoch_value is None:
        return None
    return datetime.fromtimestamp(epoch_value, tz=timezone.utc).replace(tzinfo=None)


def _to_utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _datetime_to_epoch(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return int(value.timestamp())
