## ADDED Requirements

### Requirement: Chat Completions can be served by Kiro accounts
The system MUST allow `/v1/chat/completions` requests to be served by selected Kiro accounts through the same internal Responses mapping used for OpenAI accounts. Kiro-backed Chat Completions requests MUST use Kiro upstream model `claude-sonnet-4.6`.

#### Scenario: Streaming chat request served by Kiro
- **WHEN** a streaming Chat Completions request selects a Kiro account
- **THEN** the system emits OpenAI-compatible `chat.completion.chunk` events
- **AND** the Kiro upstream payload uses model `claude-sonnet-4.6`
- **AND** the stream terminates with `data: [DONE]`

#### Scenario: Non-streaming chat request served by Kiro
- **WHEN** a non-streaming Chat Completions request selects a Kiro account
- **THEN** the system returns an OpenAI-compatible `chat.completion` object
- **AND** the Kiro upstream payload uses model `claude-sonnet-4.6`

### Requirement: Chat validation remains provider-independent
The system MUST apply existing Chat Completions request validation before account provider dispatch. Requests invalid under the Chat Completions compatibility contract MUST fail before selecting or calling a Kiro account.

#### Scenario: Invalid chat payload fails before Kiro dispatch
- **WHEN** a Chat Completions request has an invalid messages payload
- **THEN** the system returns an OpenAI-compatible validation error
- **AND** no Kiro upstream call is made
