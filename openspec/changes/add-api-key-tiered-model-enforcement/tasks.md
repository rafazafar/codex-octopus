## 1. Backend contract and persistence

- [x] 1.1 Add typed tiered enforcement models to API-key service and schemas.
- [x] 1.2 Add nullable `enforced_model_tiers` persistence and migration.
- [x] 1.3 Validate tier model targets against `allowed_models`.

## 2. Proxy enforcement

- [x] 2.1 Classify requested models into `mini` and `standard`.
- [x] 2.2 Apply tiered model/reasoning overrides without scalar fallback.
- [x] 2.3 Filter model-list responses to tier target models when tier model enforcement is configured.

## 3. Dashboard

- [x] 3.1 Add frontend schemas/types for tiered enforcement.
- [x] 3.2 Add create/edit controls for mini and standard model/reasoning enforcement.
- [x] 3.3 Display tiered enforcement on API-key detail surfaces.

## 4. Verification

- [x] 4.1 Add/update backend unit and integration tests.
- [x] 4.2 Add/update frontend tests or mocks impacted by the API-key contract.
- [x] 4.3 Run focused tests and `openspec validate`.
