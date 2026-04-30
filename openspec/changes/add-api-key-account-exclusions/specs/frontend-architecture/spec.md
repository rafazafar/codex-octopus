## ADDED Requirements

### Requirement: API-key account picker supports tri-state policy

The Settings API-key create and edit dialogs MUST expose account routing policy through a single tri-state account picker. Each account row MUST support inherited/default, explicitly allowed, and explicitly excluded states.

#### Scenario: Create key with excluded account

- **WHEN** an operator opens the API-key create dialog
- **AND** marks one account as excluded in the account picker
- **AND** submits the form
- **THEN** the create request includes that account ID in `excludedAccountIds`
- **AND** does not include the account ID in `assignedAccountIds`

#### Scenario: Edit key preserves unchanged account policy

- **WHEN** an operator edits an unrelated API-key field without changing the account picker
- **THEN** the update request omits both `assignedAccountIds` and `excludedAccountIds`

#### Scenario: Edit key sends changed allow and exclude states

- **WHEN** an operator marks one account allowed and another account excluded in the API-key edit dialog
- **THEN** the update request includes allowed accounts in `assignedAccountIds`
- **AND** includes excluded accounts in `excludedAccountIds`

#### Scenario: Account policy summary distinguishes exclusions

- **WHEN** an API key account picker has excluded accounts
- **THEN** the picker summary communicates the number of excluded accounts separately from allowed accounts
