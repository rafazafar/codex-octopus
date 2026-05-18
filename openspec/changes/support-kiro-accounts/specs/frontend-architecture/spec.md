## ADDED Requirements

### Requirement: Accounts UI labels account provider
The Accounts page MUST display each account's provider label so operators can distinguish OpenAI and Kiro accounts in the mixed pool.

#### Scenario: Provider label displayed
- **WHEN** the Accounts page lists an OpenAI account and a Kiro account
- **THEN** each row or detail view identifies the account provider

### Requirement: Accounts UI supports Kiro account onboarding
The Accounts page MUST provide an authenticated operator flow for adding or importing Kiro account credentials needed by the backend Kiro provider support.

#### Scenario: Operator adds Kiro account credentials
- **WHEN** an operator submits required Kiro credential fields
- **THEN** the frontend calls the backend account import/onboarding API with provider `kiro`
- **AND** the resulting account appears in the mixed account list with a Kiro provider label
