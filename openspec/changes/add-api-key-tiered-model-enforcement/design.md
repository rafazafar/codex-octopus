## Context

API-key model enforcement used to be scalar: `enforced_model` and `enforced_reasoning_effort` forced one model and one reasoning effort for every request. The tiered policy replaces those model/reasoning controls so operators have one clear model-enforcement concept. `enforced_service_tier` remains separate because service tier is not model classification.

## Goals / Non-Goals

**Goals:**

- Support a two-tier API-key policy for `mini` and `standard` requested model classes.
- Allow each tier to independently enforce a model and/or reasoning effort.
- Treat an empty tiered policy as no model/reasoning enforcement.
- Keep enforcement deterministic and local to the API-key/proxy policy path.

**Non-Goals:**

- Add arbitrary pattern matching or per-model rule lists.
- Add account-selection tiering.
- Change pricing, limits, service-tier enforcement, or request logging semantics.

## Decisions

- Store the tiered policy as one typed JSON column, `enforced_model_tiers`, instead of adding four nullable scalar columns. This keeps the data model compact and allows the service layer to validate the object shape before persistence.
- Classify a requested model as `mini` when its normalized slug contains a `-mini` segment. All other requested models are `standard`. This matches current OpenAI/Codex model naming and avoids a registry dependency in the hot request policy path.
- Tiered policy is the only API-key model/reasoning enforcement path. Scalar `enforced_model` and `enforced_reasoning_effort` values are not applied as fallback.
- If `enforced_model_tiers` is `NULL`, or the matching tier omits a model/reasoning field, the proxy leaves that request field unchanged.
- Filter model lists to configured tier target models when tiered model enforcement is present. If only reasoning is tiered and no tier model is configured, model-list visibility falls back to allowed-model behavior.
- Validate tier-enforced target models against `allowed_models` when `allowed_models` is configured, using the same principle as scalar enforced model validation.

## Risks / Trade-offs

- [Risk] A future model family may use a different mini naming convention. → Mitigation: keep classification isolated in a helper and add tests for current supported slugs.
- [Risk] A JSON column is less relationally queryable than scalar columns. → Mitigation: the policy is operational configuration read by key ID, not a reporting dimension.
- [Risk] Existing API keys with scalar model/reasoning values stop enforcing those values. → Mitigation: keep service-tier enforcement unchanged, hide scalar model/reasoning controls, and make the tiered policy the only visible and applied model/reasoning policy.

## Migration Plan

- Add nullable `api_keys.enforced_model_tiers` JSON column.
- Existing rows with only scalar model/reasoning values no longer enforce model/reasoning until a tiered policy is configured.
- Rollback can ignore the JSON column and restore scalar enforcement in code if needed.

## Open Questions

- None for this slice.
