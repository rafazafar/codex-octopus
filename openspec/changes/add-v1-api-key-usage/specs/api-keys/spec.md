## ADDED Requirements

### Requirement: API keys can read their own `/v1/usage`

The system SHALL expose `GET /v1/usage` for self-service usage lookup by API-key clients. The route MUST require a valid `Authorization: Bearer sk-clb-...` header even when `api_key_auth_enabled` is false globally. The response MUST include only data for the authenticated key and MUST return:

- `request_count`
- `total_tokens`
- `input_tokens`
- `cached_input_tokens`
- `output_tokens`
- `total_cost_usd`
- `usage` containing `1d`, `7d`, and `30d` windows, each with `request_count`, `total_tokens`, `input_tokens`, `cached_input_tokens`, `output_tokens`, and `total_cost_usd`
- `daily_usage` containing UTC calendar-day entries with non-zero token usage from the last 30 days, ordered oldest to newest, keyed by `DD_MM_YYYY` date string with each value containing `requests`, non-cached `tokens`, and `cost_usd`

The response MUST NOT include API key limit or upstream quota-window details.

Validation failures MUST use the existing OpenAI error envelope used by `/v1/*` routes.

#### Scenario: Missing API key is rejected

- **WHEN** a client calls `GET /v1/usage` without a Bearer token
- **THEN** the system returns 401 in the OpenAI error format

#### Scenario: Invalid API key is rejected

- **WHEN** a client calls `GET /v1/usage` with an unknown, expired, or inactive Bearer key
- **THEN** the system returns 401 in the OpenAI error format

#### Scenario: Key with no usage returns zero totals

- **WHEN** a valid API key with no request-log usage calls `GET /v1/usage`
- **THEN** the system returns `request_count: 0`, `total_tokens: 0`, `input_tokens: 0`, `cached_input_tokens: 0`, `output_tokens: 0`, `total_cost_usd: 0.0`
- **AND** the `usage.1d`, `usage.7d`, and `usage.30d` windows each return zero usage values
- **AND** `daily_usage` is empty

#### Scenario: Usage is scoped to the authenticated key

- **WHEN** multiple API keys have request-log history and one of them calls `GET /v1/usage`
- **THEN** the response includes only the usage totals for that authenticated key
- **AND** `usage.1d`, `usage.7d`, and `usage.30d` each include only request logs in their corresponding trailing window
- **AND** `daily_usage` includes only the authenticated key's request logs from the last 30 UTC calendar days
- **AND** `daily_usage` omits dates with zero token usage
- **AND** each `daily_usage` row's `requests` value equals the request count for that day
- **AND** each `daily_usage` row's `tokens` value equals billable input tokens plus output tokens for that day
- **AND** the response does not include a `limits` field

#### Scenario: Self-usage works while global proxy auth is disabled

- **WHEN** `api_key_auth_enabled` is false and a client calls `GET /v1/usage` with a valid Bearer key
- **THEN** the system still authenticates that key and returns the self-usage payload
