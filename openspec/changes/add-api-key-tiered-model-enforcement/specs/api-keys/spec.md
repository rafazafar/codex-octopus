## ADDED Requirements

### Requirement: API keys can persist tiered model enforcement

The dashboard API key CRUD surface SHALL allow callers to persist an optional `enforcedModelTiers` policy with `mini` and `standard` entries. Each entry MAY contain `model` and `reasoningEffort`. If `allowedModels` is configured, every tier `model` MUST be present in `allowedModels`.

#### Scenario: Create API key with mini and standard tier enforcement

- **WHEN** a dashboard client creates an API key with `enforcedModelTiers.mini.model: "gpt-5.4-mini"` and `enforcedModelTiers.standard.model: "gpt-5.4"`
- **THEN** the request is accepted
- **AND** subsequent reads return both tier entries

#### Scenario: Reject tier model outside allowed models

- **WHEN** a dashboard client creates or updates an API key with `allowedModels: ["gpt-5.4"]`
- **AND** `enforcedModelTiers.mini.model` is `"gpt-5.4-mini"`
- **THEN** the system rejects the request

#### Scenario: Clear tiered enforcement

- **WHEN** a dashboard client updates an API key with `enforcedModelTiers: null`
- **THEN** the persisted API key has no tiered enforcement policy
