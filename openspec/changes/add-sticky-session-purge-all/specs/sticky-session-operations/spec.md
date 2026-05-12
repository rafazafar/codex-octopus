## ADDED Requirements

### Requirement: Dashboard can purge all sticky-session mappings
The dashboard sticky-session administration surface SHALL provide an explicit, confirmed action that deletes all sticky-session mappings regardless of kind.

#### Scenario: Operator purges all sticky sessions
- **WHEN** the dashboard contains any sticky-session mappings
- **AND** the operator confirms the purge-all action
- **THEN** the system deletes matching `codex_session`, `sticky_thread`, and `prompt_cache` mappings
- **AND** the dashboard refreshes the sticky-session list

#### Scenario: Purge all is unavailable for an empty table
- **WHEN** there are no sticky-session mappings
- **THEN** the dashboard disables the purge-all action
