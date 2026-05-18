## ADDED Requirements

### Requirement: Account routing tiers are removed
The system SHALL NOT expose account routing tier values, accept account routing tier updates, or apply account routing tier weights when selecting accounts.

#### Scenario: Account list omits routing tier
- **WHEN** an admin lists accounts
- **THEN** each account summary omits any routing tier field

#### Scenario: Routing tier update endpoint removed
- **WHEN** a client calls the former routing-tier update endpoint for an account
- **THEN** the system does not provide the removed update operation

#### Scenario: Capacity routing ignores stored tiers
- **WHEN** capacity-weighted routing selects among available accounts
- **THEN** selection weight is based on capacity signals without any gold, silver, bronze, default, or stored routing-tier multiplier
