## ADDED Requirements

### Requirement: API-key usage displays pricing token parts

The system SHALL expose request-history and API-key usage summary token fields that distinguish total input, billable input, cached input, and output tokens. `billable_input_tokens` MUST be calculated as `max(0, input_tokens - cached_input_tokens)` after cached input is clamped to the available input token count. Total token fields MUST remain `input_tokens + output_tokens`.

#### Scenario: Request history includes token split

- **WHEN** a request log has `input_tokens: 1000`, `cached_input_tokens: 100`, and `output_tokens: 400`
- **THEN** the request-log API returns `input_tokens: 1000`, `billable_input_tokens: 900`, `cached_input_tokens: 100`, `output_tokens: 400`, and `tokens: 1400`

#### Scenario: API-key summary includes token split

- **WHEN** an API key has completed request-log usage
- **THEN** API-key summary responses include total input, billable input, cached input, output, total tokens, request count, and cost

#### Scenario: Shared history UI shows pricing parts

- **WHEN** Dashboard or API-key request history renders a row with cached input usage
- **THEN** the token cell shows total tokens and separates input, billable input, cached input, and output token parts
