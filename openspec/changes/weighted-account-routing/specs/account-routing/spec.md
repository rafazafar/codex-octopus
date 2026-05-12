## ADDED Requirements

### Requirement: Account routing tiers bias capacity-weighted selection
The system SHALL support account routing tiers named `gold`, `silver`, and `bronze`. When the `capacity_weighted` routing strategy selects from non-sticky eligible accounts, the system MUST multiply each account's remaining capacity weight by its configured routing-tier weight.

#### Scenario: Gold receives more weighted selections than bronze
- **WHEN** non-sticky routing selects between otherwise equivalent eligible accounts where one account is `gold` and one account is `bronze`
- **AND** the configured `gold` tier weight is greater than the configured `bronze` tier weight
- **THEN** repeated `capacity_weighted` selections choose the `gold` account more often than the `bronze` account within the test tolerance

#### Scenario: Existing safety filters still apply before tier weighting
- **WHEN** an account has a high routing-tier weight but is paused, deactivated, rate-limited, quota-exceeded, cooling down, or outside the effective health tier
- **THEN** that account is not selected ahead of an eligible lower-tier account only because of its tier weight

### Requirement: Routing tier weights are configurable
The system SHALL allow operators to configure positive numeric weights for `gold`, `silver`, and `bronze` routing tiers without changing application code. If no custom weights are configured, the default weights MUST preserve the ordering `gold` > `silver` > `bronze`.

#### Scenario: Custom tier weights change selection distribution
- **WHEN** the operator configures custom tier weights for `gold`, `silver`, and `bronze`
- **THEN** repeated non-sticky `capacity_weighted` selections reflect those configured weights together with remaining capacity

#### Scenario: Invalid tier weight config falls back safely
- **WHEN** a configured tier weight is missing, non-numeric, or not positive
- **THEN** the system uses the default weight for that tier instead of failing startup or assigning a zero selection weight

### Requirement: Undefined account tiers default to bronze
The system MUST treat accounts with no routing tier, an empty routing tier, or an unrecognized routing tier as `bronze` for selection purposes.

#### Scenario: Existing account without tier remains routable
- **WHEN** an existing eligible account has no stored routing tier
- **THEN** the account remains eligible for routing
- **AND** the account uses the configured `bronze` tier weight

#### Scenario: Unknown tier uses bronze behavior
- **WHEN** an eligible account has an unrecognized routing tier value
- **THEN** the account remains eligible for routing
- **AND** the account uses the configured `bronze` tier weight

### Requirement: Dashboard operators can assign account routing tiers
The dashboard accounts API and Accounts page MUST let authenticated operators view and persist each account's routing tier. Operators MUST be able to set `gold`, `silver`, `bronze`, or clear the override to use default bronze behavior.

#### Scenario: Account list exposes stored routing tier
- **WHEN** the dashboard lists accounts
- **THEN** each account payload includes its stored routing tier when one is configured
- **AND** accounts with no stored routing tier expose no override while still using bronze selection behavior

#### Scenario: Operator updates an account routing tier
- **WHEN** an authenticated dashboard operator sets an account routing tier to `gold`, `silver`, or `bronze`
- **THEN** the account is persisted with that routing tier
- **AND** subsequent account list responses return the saved tier
- **AND** weighted account selection uses the saved tier weight

#### Scenario: Operator clears an account routing tier
- **WHEN** an authenticated dashboard operator clears an account routing tier
- **THEN** the account stores no explicit routing tier
- **AND** subsequent account list responses expose no override
- **AND** weighted account selection treats the account as bronze

#### Scenario: Invalid routing tier is rejected
- **WHEN** an authenticated dashboard operator submits a routing tier outside `gold`, `silver`, `bronze`, or clear/default
- **THEN** the dashboard API rejects the update without changing the stored account tier

### Requirement: Sticky affinity is not redistributed by tier weights
The system MUST preserve existing sticky-affinity semantics when a sticky key already maps to an eligible account. Tier weights MUST apply when selecting a fallback or a new non-sticky account, not when deciding whether to keep an eligible existing sticky mapping.

#### Scenario: Existing eligible sticky account is retained
- **WHEN** a sticky mapping points to an eligible `bronze` account
- **AND** another eligible `gold` account exists
- **THEN** the system keeps using the sticky account according to existing sticky-affinity rules instead of replacing it only because the other account has a higher tier weight
