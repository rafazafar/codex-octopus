## ADDED Requirements

### Requirement: API key tiered model enforcement applies to upstream Responses requests

When an API key carries tiered model enforcement, the proxy SHALL classify the originally requested model as `mini` or `standard` before applying enforcement. The proxy MUST apply the matching tier's configured model and reasoning effort before forwarding upstream. Tiered model or reasoning fields MUST take precedence over scalar API-key model or reasoning enforcement for the matching request class.

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

#### Scenario: Scalar enforcement remains fallback

- **WHEN** an API key has scalar `enforcedModel: "gpt-5.4"` and no `enforcedModelTiers`
- **AND** an incoming Responses request asks for model `"gpt-5.1"`
- **THEN** the forwarded upstream payload uses model `"gpt-5.4"`
