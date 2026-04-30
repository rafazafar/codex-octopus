## ADDED Requirements

### Requirement: API keys support account exclusions

The dashboard API-key CRUD surface MUST allow operators to configure account routing policy with explicit allowed account IDs and explicit excluded account IDs. Existing `assignedAccountIds` semantics MUST continue to represent explicit allowed account IDs. `excludedAccountIds` MUST represent accounts that the key must not use.

#### Scenario: Create key with only excluded accounts

- **WHEN** an operator creates an API key with `excludedAccountIds: ["acc_a"]` and no `assignedAccountIds`
- **THEN** the key is created successfully
- **AND** subsequent reads return `assignedAccountIds: []`
- **AND** subsequent reads return `excludedAccountIds: ["acc_a"]`
- **AND** `accountAssignmentScopeEnabled` remains `false`

#### Scenario: Update key with allow and exclude policy

- **WHEN** an operator updates an API key with `assignedAccountIds: ["acc_a", "acc_b"]` and `excludedAccountIds: ["acc_b"]`
- **THEN** subsequent reads return those allowed and excluded account IDs separately
- **AND** the key's effective account policy is allowed accounts minus excluded accounts

#### Scenario: Existing assignments remain allowed

- **WHEN** an API key has pre-existing account assignment rows created before account exclusions are supported
- **THEN** those rows are treated as explicit allowed accounts
- **AND** reads return those accounts in `assignedAccountIds`
- **AND** reads do not return them in `excludedAccountIds`

#### Scenario: Empty effective account policy is accepted

- **WHEN** an operator configures a policy whose allowed accounts minus excluded accounts is empty
- **THEN** the dashboard save request succeeds
- **AND** the system stores the configured policy without special validation errors

#### Scenario: Unknown excluded account is rejected

- **WHEN** an operator creates or updates an API key with an `excludedAccountIds` entry that does not match an account
- **THEN** the dashboard API rejects the request with the existing invalid API-key payload error behavior

### Requirement: API-key account policy is enforced during proxy selection

The proxy MUST enforce API-key account policy when selecting or reusing upstream accounts. If a key has explicit allowed accounts, the base account pool MUST be limited to those accounts. Explicit excluded accounts MUST be removed from the base pool. Excluded accounts MUST also be rejected for preferred-account and HTTP bridge session reuse.

#### Scenario: Exclude-only policy uses every non-excluded eligible account

- **WHEN** an API key has `excludedAccountIds: ["acc_a"]` and no assigned account IDs
- **AND** normal routing considers accounts `acc_a` and `acc_b`
- **THEN** `acc_a` is not eligible for that key
- **AND** `acc_b` remains eligible if it passes normal global account eligibility rules

#### Scenario: Allow policy subtracts excluded accounts

- **WHEN** an API key has `assignedAccountIds: ["acc_a", "acc_b"]` and `excludedAccountIds: ["acc_b"]`
- **THEN** only `acc_a` remains eligible for that key

#### Scenario: Excluded preferred account is not reused

- **WHEN** a request carries a preferred account ID that is listed in the API key's excluded account IDs
- **THEN** the proxy MUST NOT reuse that preferred account
- **AND** selection continues through the remaining eligible pool

#### Scenario: Excluded bridge session is not reused

- **WHEN** an HTTP bridge session is attached to an account listed in the current API key's excluded account IDs
- **THEN** the bridge session is not valid for that API key request
