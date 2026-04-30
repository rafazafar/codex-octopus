## ADDED Requirements

### Requirement: Responses bridge account continuity respects API-key exclusions

Responses HTTP bridge and websocket continuity paths MUST respect API-key account exclusions when attempting to reuse an existing upstream account or session.

#### Scenario: Previous Responses bridge account is excluded

- **WHEN** a Responses continuity request would reuse a previous upstream account
- **AND** the current API key excludes that account
- **THEN** the proxy does not reuse that excluded account
- **AND** the request falls back to selecting from the remaining eligible account pool
