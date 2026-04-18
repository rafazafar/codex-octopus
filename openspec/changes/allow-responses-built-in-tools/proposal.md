## Why

Newer Codex Desktop builds send built-in Responses tool definitions in WebSocket `response.create` payloads. `codex-lb` currently rejects some of those tools locally during Responses payload validation, returning `invalid_request_error` with `param = "tools"` before the request can reach upstream. For Responses-family proxying, tool support should be decided by upstream unless the proxy itself cannot represent the payload.

## What Changes

- Allow built-in tools in Responses-family payloads, including HTTP `/v1/responses`, HTTP `/backend-api/codex/responses`, and their WebSocket equivalents.
- Continue forwarding accepted built-in tool definitions unchanged.
- Preserve existing Chat Completions behavior: `/v1/chat/completions` continues to reject unsupported built-in tools other than `web_search` until that compatibility surface is intentionally expanded.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `responses-api-compat`: accept built-in Responses tools as pass-through payload data.

## Impact

- Code: `app/core/openai/requests.py`, `app/core/openai/chat_requests.py`
- Tests: `tests/integration/test_openai_compat_features.py`, `tests/integration/test_proxy_websocket_responses.py`
