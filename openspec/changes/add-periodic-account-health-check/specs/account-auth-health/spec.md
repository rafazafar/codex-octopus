## ADDED Requirements

### Requirement: Periodic account auth-health checks

The system MUST periodically inspect managed accounts for token viability before normal routing depends on them.

#### Scenario: Expired access token without refresh token requires re-login

- **GIVEN** an account is not paused or already deactivated
- **AND** its access token expiry is at or before the configured refresh leeway
- **AND** it has no usable refresh token
- **WHEN** the periodic auth-health check runs
- **THEN** the account is marked `deactivated`
- **AND** the deactivation reason tells the operator that re-login is required

#### Scenario: Expired access token with refresh token is refreshed

- **GIVEN** an account is not paused or already deactivated
- **AND** its access token expiry is at or before the configured refresh leeway
- **AND** it has a usable refresh token
- **WHEN** the periodic auth-health check runs
- **THEN** the system attempts a forced token refresh
- **AND** a successful refresh keeps the account available

#### Scenario: Transient refresh failures do not deactivate accounts

- **GIVEN** an account has a usable refresh token
- **AND** the forced refresh fails with a transient error
- **WHEN** the periodic auth-health check runs
- **THEN** the account lifecycle status is not changed by the health check
