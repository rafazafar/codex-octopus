## ADDED Requirements

### Requirement: API key tiered model enforcement applies to upstream Responses requests

When an API key carries tiered model enforcement, the proxy SHALL classify the originally requested model as `mini` or `standard` before applying enforcement. The proxy MUST apply the matching tier's configured model and reasoning effort before forwarding upstream. Tiered model/reasoning fields are the only API-key model/reasoning enforcement path.

#### Scenario: Mini request uses mini tier

- **WHEN** an API key is configured with `enforcedModelTiers.mini.model: "gpt-5.4-mini"` and `enforcedModelTiers.mini.reasoningEffort: "low"`
- **AND** an incoming Responses request asks for model `"gpt-5.1-codex-mini"`
- **THEN** the forwarded upstream payload uses model `"gpt-5.4-mini"`
- **AND** the forwarded upstream payload uses reasoning effort `"low"`

#### Scenario: Standard request uses standard tier

- **WHEN** an API key is configured with `enforcedModelTiers.standard.model: "gpt-5.4"` and `enforcedModelTiers.standard.reasoningEffort: "high"`
- **AND** an incoming Responses request asks for model `"gpt-5.3-codex"`
- **THEN** the forwarded upstream payload uses model `"gpt-5.4"`
- **AND** the forwarded upstream payload uses reasoning effort `"high"`

#### Scenario: Empty tiered enforcement does not enforce model or reasoning

- **WHEN** an API key has no `enforcedModelTiers`
- **AND** an incoming Responses request asks for model `"gpt-5.1"` and reasoning effort `"medium"`
- **THEN** the forwarded upstream payload keeps model `"gpt-5.1"`
- **AND** the forwarded upstream payload keeps reasoning effort `"medium"`

#### Scenario: Partial tiered enforcement only changes configured fields

- **WHEN** an API key is configured with `enforcedModelTiers.standard.model: "gpt-5.4"` and no standard reasoning effort
- **AND** an incoming Responses request asks for model `"gpt-5.3-codex"` and reasoning effort `"medium"`
- **THEN** the forwarded upstream payload uses model `"gpt-5.4"`
- **AND** the forwarded upstream payload keeps reasoning effort `"medium"`
