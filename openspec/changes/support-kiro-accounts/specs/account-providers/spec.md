## ADDED Requirements

### Requirement: Accounts are provider-aware
The system SHALL support account provider values `openai` and `kiro`. Existing accounts with no stored provider MUST behave as `openai` accounts. Account API summaries MUST expose each account provider so dashboard clients can label mixed provider accounts.

#### Scenario: Existing account defaults to OpenAI provider
- **WHEN** an existing account row has no explicit provider value after migration
- **THEN** the system treats the account as provider `openai`
- **AND** existing OpenAI routing behavior is preserved

#### Scenario: Account list exposes provider labels
- **WHEN** the dashboard lists accounts
- **THEN** each account summary includes provider `openai` or `kiro`

### Requirement: Kiro credentials are stored securely
The system MUST store Kiro credentials needed for generation and refresh without exposing secret values in dashboard summaries, request logs, or console logs. Kiro accounts MUST support access token, refresh token, auth method, client id, client secret, region, expiration timestamp, machine id, and profile ARN fields as applicable.

#### Scenario: Kiro account import persists refresh metadata
- **WHEN** an operator imports a Kiro account with refresh token, auth method, client metadata, region, and expiration
- **THEN** the system persists the account as provider `kiro`
- **AND** the system can later refresh the access token without requiring OpenAI auth claims

#### Scenario: Kiro secrets are redacted
- **WHEN** the dashboard lists or exports account summaries
- **THEN** Kiro access tokens, refresh tokens, client secrets, and other secret credential material are not exposed in plain text

### Requirement: Mixed provider accounts share one routing pool
The system MUST route OpenAI and Kiro accounts through the same account selection pool for compatible generation endpoints. Existing API-key account assignments, account exclusions, routing tiers, sticky affinity, cooldown, health status, and failover rules MUST apply to both providers unless a provider is incompatible with the requested endpoint.

#### Scenario: Mixed provider pool can select either provider
- **WHEN** one eligible OpenAI account and one eligible Kiro account are available for a compatible generation request
- **THEN** account selection considers both accounts in the same pool according to existing routing rules

#### Scenario: API key assignment includes Kiro accounts
- **WHEN** an API key is assigned to a Kiro account
- **THEN** compatible generation requests authenticated with that key may select the assigned Kiro account
- **AND** unassigned accounts remain excluded according to existing assignment rules

#### Scenario: Sticky affinity can pin a Kiro account
- **WHEN** a compatible generation request creates sticky affinity to a Kiro account
- **THEN** subsequent compatible requests with the same sticky key use the same Kiro account while it remains eligible under existing sticky-affinity rules

### Requirement: Provider dispatch follows selected account provider
After selecting an account, the system MUST dispatch upstream requests according to that account's provider. OpenAI accounts MUST use the existing ChatGPT/Codex upstream adapter. Kiro accounts MUST use the Kiro upstream adapter.

#### Scenario: OpenAI account uses existing upstream path
- **WHEN** the selected account provider is `openai`
- **THEN** the request is sent through the existing ChatGPT/Codex upstream client

#### Scenario: Kiro account uses Kiro upstream path
- **WHEN** the selected account provider is `kiro`
- **THEN** the request is translated to a Kiro generation payload
- **AND** the request is sent through the Kiro upstream client

### Requirement: Kiro token refresh is provider-specific
The system MUST refresh Kiro access tokens using Kiro-compatible refresh flows and MUST NOT use OpenAI OAuth refresh endpoints for Kiro accounts.

#### Scenario: Kiro account nearing expiration is refreshed
- **WHEN** a selected Kiro account access token is expired or near expiration
- **THEN** the system refreshes the token using the Kiro account's auth method and refresh metadata before sending the upstream request

#### Scenario: Kiro permanent auth failure affects only that account
- **WHEN** Kiro token refresh fails with a permanent authentication error
- **THEN** the selected Kiro account is marked unhealthy or deactivated according to existing permanent failure behavior
- **AND** other eligible accounts remain available for future requests

### Requirement: Kiro upstream model is fixed to Claude Sonnet 4.6
For Kiro-backed generation requests, the system MUST send `claude-sonnet-4.6` as the Kiro upstream model regardless of the downstream requested model.

#### Scenario: Requested model is mapped to Claude Sonnet 4.6 for Kiro
- **WHEN** a compatible generation request asks for any model and the selected account provider is `kiro`
- **THEN** the Kiro upstream payload uses model `claude-sonnet-4.6`
- **AND** the system records enough provider/upstream detail for operators to identify that Kiro used `claude-sonnet-4.6`
