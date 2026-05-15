## Purpose

This change lets codex-lb act as one load balancer for both ChatGPT/Codex accounts and Kiro accounts. Operators should not need separate base URLs or separate pools. They should add accounts, see a provider label, and let normal routing choose a healthy eligible account.

## Reference Implementation Notes

Use Kiro-Go's OpenAI-compatible path as a behavioral reference, especially:

- `proxy/translator.go` for OpenAI/Claude-to-Kiro payload mapping and model alias handling.
- `proxy/kiro.go` for Kiro generation endpoints, request headers, endpoint fallback, and AWS event-stream parsing.
- `proxy/kiro_headers.go` for Kiro user-agent and AWS-style header shape.
- `auth/oidc.go` for Kiro token refresh behavior.
- `proxy/handler.go` OpenAI chat route for streaming/non-streaming response shaping.

Do not reuse Kiro-Go's `/backend-api/codex` implementation as the design basis. The Kiro path in codex-lb should translate from codex-lb's internal Responses model instead.

## Decisions And Alternatives

Native provider support is preferred over running Kiro-Go as a sidecar. The sidecar option would be faster to prototype, but codex-lb would lose clean ownership over API-key assignment, account exclusions, sticky affinity, request logs, failover, health state, and future migrations.

Provider-specific branches should happen after account selection. This keeps one shared pool and avoids forking routing logic. Eligibility filters still matter for endpoints that a provider cannot serve, such as audio transcription.

Kiro generation always uses `claude-sonnet-4.6`. That is the provider mapping contract for the first tranche. Future work can add configurable Kiro model selection, but this change should avoid that extra policy surface.

## Constraints

- Keep `spec.md` normative and testable; use this context file for rationale and examples.
- Do not commit or expose tokens. Kiro client id/secret and token fields must follow existing encryption/redaction patterns.
- Public client endpoints remain stable.
- Existing OpenAI account imports must keep working without provider fields.
- Existing request routing, tiers, API-key assignment, account exclusions, and sticky affinity should keep their current behavior unless a provider compatibility filter applies.

## Example

A client sends:

```json
{
  "model": "gpt-5.5",
  "messages": [{"role": "user", "content": "hello"}],
  "stream": true
}
```

`/v1/chat/completions` maps the request to internal Responses. The load balancer selects a Kiro account. The Kiro dispatcher converts the Responses input to a Kiro payload, sets Kiro `modelId` to `claude-sonnet-4.6`, streams Kiro event-stream text back as OpenAI-compatible chat chunks, and logs the selected account/provider/upstream model.

## Failure Modes

- A Kiro refresh token expires: mark the account unhealthy/deactivated using the closest existing permanent auth failure flow.
- Kiro returns quota exhaustion before output commits: mark/cool down that account and retry another eligible account when budget allows.
- Kiro emits malformed event-stream frames: surface a stable upstream error and record request-log details.
- A transcription request has only Kiro accounts available: return a stable no-compatible-account error instead of attempting Kiro.
