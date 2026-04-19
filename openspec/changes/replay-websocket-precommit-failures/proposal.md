## Why

Backend Codex websocket requests can still surface upstream account-health failures such as `usage_limit_reached` even when another account could satisfy the request. Today websocket connect-phase failover exists, but once the upstream websocket is open a terminal `response.failed` ends the current request and only reconnects for later requests. That forces clients to resend prompts that could have been replayed safely on another account.

## What Changes

- Replay the current websocket `response.create` request on a different account when the upstream returns a retryable account-health failure before any downstream frame for that request has been sent.
- Keep the existing no-replay safety boundary once the request has emitted any downstream frame.
- Preserve the last retryable upstream error as the surfaced error when replay candidates are exhausted instead of collapsing to generic `no_accounts`.
- Add focused websocket replay logging and counters for operator visibility.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `responses-api-compat`: backend websocket Responses requests may transparently replay on another account after pre-commit `usage_limit_reached`-style failures.

## Impact

- Code: `app/modules/proxy/service.py`, `app/core/metrics/prometheus.py`
- Tests: `tests/integration/test_proxy_websocket_responses.py`
