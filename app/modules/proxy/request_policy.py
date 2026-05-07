from __future__ import annotations

import logging

from pydantic import ValidationError

from app.core.errors import OpenAIErrorEnvelope, openai_error
from app.core.exceptions import ProxyModelNotAllowed
from app.core.openai.requests import ResponsesCompactRequest, ResponsesReasoning, ResponsesRequest
from app.core.openai.v1_requests import V1ResponsesRequest
from app.core.types import JsonValue
from app.core.utils.request_id import get_request_id
from app.modules.api_keys.service import ApiKeyData

logger = logging.getLogger(__name__)


def is_mini_model(model: str | None) -> bool:
    if not model:
        return False
    normalized = model.strip().lower()
    return normalized.endswith("-mini") or "-mini-" in normalized


def get_tier_enforced_models(api_key: ApiKeyData | None) -> set[str]:
    if api_key is None or api_key.enforced_model_tiers is None:
        return set()
    models: set[str] = set()
    for tier in (api_key.enforced_model_tiers.mini, api_key.enforced_model_tiers.standard):
        if tier is not None and tier.model:
            models.add(tier.model)
    return models


def get_effective_model_for_api_key(api_key: ApiKeyData | None, requested_model: str) -> str:
    if api_key is None:
        return requested_model
    tier = _tier_for_requested_model(api_key, requested_model)
    if tier is not None and tier.model is not None:
        return tier.model
    if api_key.enforced_model is not None:
        return api_key.enforced_model
    return requested_model


def validate_model_access(api_key: ApiKeyData | None, model: str | None) -> None:
    if api_key is None:
        return
    allowed_models = api_key.allowed_models
    if not allowed_models:
        return
    if model is None or model in allowed_models:
        return
    raise ProxyModelNotAllowed(f"This API key does not have access to model '{model}'")


def apply_api_key_enforcement(
    payload: ResponsesRequest | ResponsesCompactRequest,
    api_key: ApiKeyData | None,
) -> None:
    if api_key is None:
        return

    tier = _tier_for_requested_model(api_key, payload.model)
    enforced_model = tier.model if tier is not None and tier.model is not None else api_key.enforced_model
    enforced_reasoning_effort = (
        tier.reasoning_effort
        if tier is not None and tier.reasoning_effort is not None
        else api_key.enforced_reasoning_effort
    )

    if enforced_model and payload.model != enforced_model:
        logger.info(
            "api_key_model_enforced request_id=%s key_id=%s requested_model=%s enforced_model=%s",
            get_request_id(),
            api_key.id,
            payload.model,
            enforced_model,
        )
        payload.model = enforced_model

    if enforced_reasoning_effort is not None:
        requested_effort = payload.reasoning.effort if payload.reasoning else None
        if payload.reasoning is None:
            payload.reasoning = ResponsesReasoning(effort=enforced_reasoning_effort)
        else:
            payload.reasoning.effort = enforced_reasoning_effort
        if requested_effort != enforced_reasoning_effort:
            logger.info(
                "api_key_reasoning_enforced request_id=%s key_id=%s requested_effort=%s enforced_effort=%s",
                get_request_id(),
                api_key.id,
                requested_effort,
                enforced_reasoning_effort,
            )

    if api_key.enforced_service_tier is not None:
        requested_service_tier = getattr(payload, "service_tier", None)
        setattr(payload, "service_tier", api_key.enforced_service_tier)
        if requested_service_tier != api_key.enforced_service_tier:
            logger.info(
                "api_key_service_tier_enforced request_id=%s key_id=%s "
                "requested_service_tier=%s enforced_service_tier=%s",
                get_request_id(),
                api_key.id,
                requested_service_tier,
                api_key.enforced_service_tier,
            )


def _tier_for_requested_model(api_key: ApiKeyData, requested_model: str | None):
    tiers = api_key.enforced_model_tiers
    if tiers is None:
        return None
    if is_mini_model(requested_model):
        return tiers.mini
    return tiers.standard


def openai_validation_error(exc: ValidationError) -> OpenAIErrorEnvelope:
    error = openai_invalid_payload_error()
    if exc.errors():
        first = exc.errors()[0]
        loc = first.get("loc", [])
        if isinstance(loc, (list, tuple)):
            param = ".".join(str(part) for part in loc if part != "body")
            if param:
                error["error"]["param"] = param
    return error


def openai_invalid_payload_error(param: str | None = None) -> OpenAIErrorEnvelope:
    error = openai_error("invalid_request_error", "Invalid request payload", error_type="invalid_request_error")
    if param:
        error["error"]["param"] = param
    return error


def normalize_responses_request_payload(
    payload: dict[str, JsonValue],
    *,
    openai_compat: bool,
) -> ResponsesRequest:
    if openai_compat:
        return V1ResponsesRequest.model_validate(payload).to_responses_request()
    return ResponsesRequest.model_validate(payload)
