## ADDED Requirements

### Requirement: Accounts carry an independent expiry date

The system MUST persist an account-level expiry date independently from the account lifecycle `status`.

#### Scenario: Expiry remains distinct from lifecycle status

- **WHEN** an account has a stored expiry date
- **THEN** the system preserves the account's existing lifecycle `status`
- **AND** expiry does not overwrite or redefine that status

#### Scenario: Accounts API returns expiry state

- **WHEN** the dashboard requests account list or detail data
- **THEN** each returned account includes `expiresAt` when present
- **AND** each returned account includes a derived `isExpired` flag computed by the backend

### Requirement: Add and import paths default expiry to 30 days

The system MUST assign a default expiry date 30 days after add/import whenever the incoming account payload does not provide expiry.

#### Scenario: OAuth or auth.json add defaults expiry

- **WHEN** a new account is added through a path that does not carry expiry data
- **THEN** the stored account expiry is set to approximately 30 days after the write time

#### Scenario: Re-import without expiry resets the lease

- **WHEN** an existing account is imported or updated from a payload that does not include expiry
- **THEN** the stored account expiry is reset to approximately 30 days after the import time

### Requirement: Portable import and export preserve expiry

The portable account JSON format MUST round-trip account expiry when the payload provides it.

#### Scenario: Portable import preserves supplied expiry

- **WHEN** a portable account payload includes an expiry value
- **THEN** the imported account stores that exact effective expiry time

#### Scenario: Portable export includes expiry

- **WHEN** the dashboard exports accounts in the portable JSON format
- **THEN** each exported account record includes its stored expiry when one exists

#### Scenario: Invalid portable expiry rejects the batch

- **WHEN** any account record in a portable import batch contains an invalid expiry value
- **THEN** the import request fails with a handled validation error
- **AND** none of the records in that batch are persisted

### Requirement: Expired accounts are excluded from normal selection

The system MUST treat expired accounts as ineligible for normal routing/selection without removing them from dashboard management surfaces.

#### Scenario: Expired account is excluded from routing

- **WHEN** normal account selection considers an account whose expiry time is at or before the current time
- **THEN** that account is not eligible for selection

#### Scenario: Expired account remains visible in Accounts UI

- **WHEN** an account is expired
- **THEN** the dashboard still returns it in the Accounts list/detail responses
- **AND** operators can inspect and edit its expiry

### Requirement: Operators can manually edit account expiry

The dashboard MUST provide a focused account expiry update contract that supports setting, extending, and clearing expiry.

#### Scenario: Set or extend account expiry

- **WHEN** an operator submits a valid expiry timestamp for an existing account
- **THEN** the system updates that account's stored expiry to the submitted value

#### Scenario: Clear account expiry

- **WHEN** an operator submits a null expiry value for an existing account
- **THEN** the system clears the stored expiry for that account

#### Scenario: Missing account update returns not found

- **WHEN** an operator updates expiry for an account that does not exist
- **THEN** the dashboard returns the existing account-not-found error behavior
