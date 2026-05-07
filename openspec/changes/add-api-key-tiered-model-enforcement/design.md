## Context

API-key enforcement is currently scalar: `enforced_model`, `enforced_reasoning_effort`, and `enforced_service_tier` are optional columns on `api_keys`. The proxy mutates the normalized Responses payload in `app/modules/proxy/request_policy.py` before forwarding upstream. The model-list endpoints also narrow visible models to the single enforced model when scalar model enforcement is configured.

## Goals / Non-Goals

**Goals:**

- Support a two-tier API-key policy for `mini` and `standard` requested model classes.
- Allow each tier to independently enforce a model and/or reasoning effort.
- Preserve existing scalar enforcement for existing API keys and simple one-model policies.
- Keep enforcement deterministic and local to the API-key/proxy policy path.

**Non-Goals:**

- Add arbitrary pattern matching or per-model rule lists.
- Add account-selection tiering.
- Change pricing, limits, service-tier enforcement, or request logging semantics.

## Decisions

- Store the tiered policy as one typed JSON column, `enforced_model_tiers`, instead of adding four nullable scalar columns. This keeps the data model compact and allows the service layer to validate the object shape before persistence.
- Classify a requested model as `mini` when its normalized slug contains a `-mini` segment. All other requested models are `standard`. This matches current OpenAI/Codex model naming and avoids a registry dependency in the hot request policy path.
- Give tiered policy precedence over scalar model/reasoning enforcement when at least one matching tier field is configured. Scalar fields remain fallback behavior when the tiered policy is absent or the matching tier omits a field.
- Filter model lists to configured tier target models when tiered model enforcement is present. If only reasoning is tiered and no tier model is configured, model-list visibility falls back to allowed-model behavior.
- Validate tier-enforced target models against `allowed_models` when `allowed_models` is configured, using the same principle as scalar enforced model validation.

## Risks / Trade-offs

- [Risk] A future model family may use a different mini naming convention. → Mitigation: keep classification isolated in a helper and add tests for current supported slugs.
- [Risk] A JSON column is less relationally queryable than scalar columns. → Mitigation: the policy is operational configuration read by key ID, not a reporting dimension.
- [Risk] Combining scalar and tiered policies could confuse operators. → Mitigation: document precedence in specs and make the UI visually group tiered settings separately.

## Migration Plan

- Add nullable `api_keys.enforced_model_tiers` JSON column.
- Existing rows keep scalar behavior because the new column defaults to `NULL`.
- Rollback can ignore the JSON column and continue using scalar enforcement.

## Open Questions

- None for this slice.
