## MODIFIED Requirements

### Requirement: Dashboard shell routes

The dashboard shell SHALL expose a dedicated `Onboarding` route for operator-guided client setup alongside the existing Dashboard, Accounts, APIs, and Settings routes, and the onboarding route SHALL remain reachable without passing through the dashboard auth gate.

#### Scenario: Open the onboarding route from primary navigation

- **WHEN** an authenticated operator uses the main app navigation
- **THEN** the shell exposes an `Onboarding` destination
- **AND** opening it renders a dedicated onboarding page instead of redirecting to another surface

#### Scenario: Open onboarding without a dashboard session

- **WHEN** an unauthenticated visitor opens `/onboarding`
- **THEN** the app renders the onboarding page instead of the dashboard sign-in flow
- **AND** non-onboarding dashboard routes remain behind the auth gate

### Requirement: Client onboarding flow

The app SHALL provide an onboarding flow that generates environment-aware setup guidance for supported clients using a minimal public bootstrap contract, while reserving live validation for authenticated dashboard sessions.

#### Scenario: Generate Codex CLI setup from live runtime facts

- **WHEN** an operator opens the onboarding page and selects `Codex CLI`
- **THEN** the page renders a config snippet that targets `/backend-api/codex`
- **AND** the rendered output uses live public bootstrap values where available, including API-key requirements and connect-address guidance

#### Scenario: Generate OpenCode setup from live runtime facts

- **WHEN** an operator selects `OpenCode`
- **THEN** the page renders a config snippet that targets `/v1`
- **AND** the output reflects whether API-key auth is enabled

#### Scenario: Render onboarding from the public bootstrap contract

- **WHEN** the onboarding page loads without a dashboard session
- **THEN** it reads only the minimal anonymous bootstrap contract
- **AND** that contract includes connect-address guidance and API-key-auth state
- **AND** it does not expose broader dashboard settings or account state

#### Scenario: Validate readiness and client reachability

- **WHEN** an authenticated operator runs onboarding validation
- **THEN** the page checks readiness via `/health/ready`
- **AND** the page checks the relevant model-list endpoint for the selected client
- **AND** validation results distinguish successful connectivity from auth mismatch or endpoint failure

#### Scenario: Hide live validation from anonymous visitors

- **WHEN** an unauthenticated visitor opens the onboarding page
- **THEN** the page explains that live validation requires dashboard sign-in
- **AND** it does not expose active validation controls

#### Scenario: Show targeted remediation for API-key mismatch

- **WHEN** onboarding validation receives `401` from the selected client model-list endpoint while API-key auth is enabled
- **THEN** the page explains that the client must use a dashboard-generated API key
- **AND** the page does not collapse that state into a generic “request failed” error
