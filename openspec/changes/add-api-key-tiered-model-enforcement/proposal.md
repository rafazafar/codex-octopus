## Why

API keys can currently force one model and one reasoning effort for every proxied request. Operators need a tiered policy so mini-model requests can be forced to one model/thinking profile while standard requests are forced to a different model/thinking profile.

## What Changes

- Add optional API-key tiered model enforcement for two request classes: `mini` and `standard`.
- Persist, return, create, and update tiered enforcement policy through the dashboard API.
- Apply the matching tier before forwarding Responses-compatible requests upstream.
- Keep existing scalar `enforcedModel` / `enforcedReasoningEffort` behavior for simple policies and backward compatibility.
- Expose tiered enforcement in the API-key create/edit dashboard surface.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `api-keys`: API-key CRUD can persist and return tiered model enforcement policy.
- `responses-api-compat`: Responses proxy enforcement can choose model and reasoning overrides from the requested model class.

## Impact

- Backend API-key schema/service/repository/model layers.
- Database migration for the new tiered policy column.
- Proxy request policy and model-list filtering.
- Dashboard API-key create/edit/info components and frontend schemas.
- Unit and integration tests covering persistence, validation, model-list filtering, and request enforcement.
