## ADDED Requirements

### Requirement: Replay websocket Responses requests after pre-commit account-health failure
For websocket `response.create` requests on the backend Codex Responses routes, the service MUST replay the current request on another eligible account when the upstream returns a retryable account-health failure before any downstream frame for that request has been forwarded.

#### Scenario: websocket request replays on `usage_limit_reached` before `response.created`
- **WHEN** the client sends a websocket `response.create` request
- **AND** the upstream returns `response.failed` with `usage_limit_reached`
- **AND** the request has not forwarded any downstream frame
- **AND** no other request is in flight on that upstream websocket
- **THEN** the service replays the same request on another eligible account
- **AND** the client does not receive the hidden failing terminal frame

#### Scenario: websocket request surfaces final retryable error after replay exhaustion
- **WHEN** the client sends a websocket `response.create` request
- **AND** each eligible replay attempt fails with a retryable account-health error before any downstream frame
- **THEN** the service surfaces the last retryable upstream error for that request
- **AND** it does not rewrite the error into `no_accounts`

#### Scenario: websocket request does not replay after any downstream frame
- **WHEN** the client has already received `response.created` or any later frame for the request
- **AND** the upstream then returns `response.failed` with a retryable account-health error
- **THEN** the service surfaces that failure
- **AND** it does not replay the current request on another account
