## ADDED Requirements

### Requirement: Allow built-in tools in Responses
The service MUST accept Responses-family requests that include built-in tool definitions. The service MUST normalize `web_search_preview` to `web_search`. The service MUST forward accepted built-in tool definitions unchanged except for documented aliases.

#### Scenario: built-in tool accepted over HTTP
- **WHEN** the client sends `/v1/responses` with a built-in tool such as `image_generation`, `file_search`, `code_interpreter`, or `computer_use_preview`
- **THEN** the service accepts the request and forwards the tool definition unchanged except for documented aliases

#### Scenario: built-in tool accepted over WebSocket
- **WHEN** the client sends a WebSocket `response.create` payload with built-in tools
- **THEN** the service accepts the request and forwards the tool definitions unchanged except for documented aliases
