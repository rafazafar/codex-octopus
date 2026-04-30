## 1. Specs

- [x] 1.1 Add an API-key self-usage requirement for `GET /v1/usage`.
- [x] 1.2 Validate OpenSpec changes.

## 2. Tests

- [x] 2.1 Add integration coverage for missing/invalid API keys.
- [x] 2.2 Add integration coverage for zero-usage responses, per-key usage scoping, hidden limits, and daily usage breakdowns.
- [x] 2.3 Add integration coverage that `GET /v1/usage` still works when global proxy API-key auth is disabled.

## 3. Implementation

- [x] 3.1 Add self-usage API-key validation that always requires a valid Bearer key.
- [x] 3.2 Add `GET /v1/usage` and return usage totals plus daily usage for the authenticated key.
- [x] 3.3 Reuse API-key repository/service aggregation instead of scanning all keys.
