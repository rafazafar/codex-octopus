## ADDED Requirements

### Requirement: System health summary exposes cross-account risk states
The dashboard backend SHALL expose a system-health summary that reports the highest-severity active cross-account risk condition derived from account availability, aggregate depletion risk, and recent normalized request-log outcomes.

#### Scenario: Account pool collapse becomes a critical system-health alert
- **WHEN** the proportion of `active` accounts falls below the configured critical threshold
- **THEN** `GET /api/system-health` returns `status: "critical"`
- **AND** the alert identifies account-pool collapse
- **AND** the payload includes account counts and an investigation route

#### Scenario: Capacity exhaustion risk becomes a critical system-health alert
- **WHEN** aggregate depletion risk reaches the critical level for a tracked usage window
- **THEN** `GET /api/system-health` returns a critical alert describing imminent capacity exhaustion

#### Scenario: Rate-limit wave becomes a warning system-health alert
- **WHEN** normalized recent request-log outcomes show `rate_limit` above the configured warning threshold with sufficient traffic volume
- **THEN** `GET /api/system-health` returns `status: "warning"`
- **AND** the alert identifies a rate-limit wave
