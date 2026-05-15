## ADDED Requirements

### Requirement: Responses requests support Kiro-backed accounts
The system MUST support `/v1/responses` and `/backend-api/codex/responses` generation requests using selected Kiro accounts. When a Kiro account is selected, the system MUST translate the internal Responses request into a Kiro generation payload, send it through the Kiro upstream adapter, and return OpenAI-compatible Responses output.

#### Scenario: Streaming Responses request served by Kiro
- **WHEN** a streaming Responses request selects a Kiro account
- **THEN** the system streams OpenAI-compatible Responses events to the downstream client
- **AND** the Kiro upstream payload uses model `claude-sonnet-4.6`

#### Scenario: Non-streaming Responses request served by Kiro
- **WHEN** a non-streaming Responses request selects a Kiro account
- **THEN** the system returns a single OpenAI-compatible response object
- **AND** the Kiro upstream payload uses model `claude-sonnet-4.6`

### Requirement: Kiro Responses translation preserves supported inputs
For Kiro-backed Responses requests, the system MUST preserve supported instructions, user text, image inputs, assistant history, function/custom tools, tool results, and reasoning hints when translating to Kiro payloads. Unsupported payload features MUST fail with an OpenAI-compatible error envelope instead of being silently ignored.

#### Scenario: Responses text and instructions are translated
- **WHEN** a Kiro-backed Responses request includes instructions and user text input
- **THEN** the Kiro payload includes equivalent system/task context and current user content

#### Scenario: Responses tools are translated
- **WHEN** a Kiro-backed Responses request includes supported function or custom tools
- **THEN** the Kiro payload includes equivalent Kiro tool specifications
- **AND** Kiro tool-use events are returned as compatible Responses output items

### Requirement: Kiro compact compatibility is explicit
For Kiro-backed `/backend-api/codex/responses/compact` requests, the system MUST either return a compatible synthetic compact response that does not claim real encrypted reasoning state, or return a stable OpenAI-compatible unsupported error. The chosen behavior MUST be covered by tests.

#### Scenario: Kiro compact does not fabricate encrypted reasoning state
- **WHEN** a compact request is served through Kiro-compatible behavior
- **THEN** the response does not claim preserved OpenAI encrypted reasoning state
