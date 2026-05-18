## ADDED Requirements

### Requirement: Accounts UI omits routing tiers
The frontend SHALL NOT display account routing tier labels or controls.

#### Scenario: Account list has no routing tier label
- **WHEN** an admin views the accounts list
- **THEN** account rows show account identity, provider, status, plan, and usage information without gold, silver, bronze, or default tier labels

#### Scenario: Account detail has no routing tier control
- **WHEN** an admin views account details
- **THEN** no routing-tier selector or routing-tier update action is available

### Requirement: Application shell omits global incident banner
The frontend SHALL NOT render the global system-health incident banner in the application shell.

#### Scenario: System-health alert does not create shell banner
- **WHEN** the system-health endpoint reports a warning or critical alert
- **THEN** the application shell does not show a persistent global alert/banner
