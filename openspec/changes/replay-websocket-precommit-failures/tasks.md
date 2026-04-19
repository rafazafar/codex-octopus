## 1. Websocket request replay

- [ ] 1.1 Add request-local websocket replay eligibility and state tracking for pre-commit retryable account-health failures.
- [ ] 1.2 Replay the current `response.create` on a new upstream account without forwarding the hidden failing frame.
- [ ] 1.3 Surface the last retryable upstream error when replay candidates are exhausted.

## 2. Observability

- [ ] 2.1 Add websocket replay decision logs and Prometheus counters.
- [ ] 2.2 Keep hidden replay attempts out of client-visible request-log rows.

## 3. Validation

- [ ] 3.1 Add websocket replay integration coverage for success, exhaustion, and safety-boundary scenarios.
- [ ] 3.2 Run focused websocket proxy tests.
- [ ] 3.3 Run OpenSpec validation.
