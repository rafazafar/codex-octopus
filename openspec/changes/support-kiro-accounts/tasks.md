## 1. Spec And Data Model

- [ ] 1.1 Add provider-aware account requirements and migration plan for `openai` and `kiro` accounts.
- [ ] 1.2 Add account-provider persistence with backward-compatible `openai` default for existing accounts.
- [ ] 1.3 Add encrypted Kiro credential fields and validation/redaction behavior.
- [ ] 1.4 Expose provider labels in account summaries and dashboard schemas.

## 2. Account Import And Refresh

- [ ] 2.1 Add Kiro account import/onboarding payload support for access token, refresh token, client metadata, auth method, region, expiration, machine id, and profile ARN.
- [ ] 2.2 Add Kiro token refresh service for OIDC and social refresh flows.
- [ ] 2.3 Keep OpenAI auth JSON and portable import/export behavior backward-compatible.
- [ ] 2.4 Update account health/usage refresh to use provider-specific checks or skip incompatible provider checks safely.

## 3. Kiro Upstream Adapter

- [ ] 3.1 Add Kiro request/header builder using Kiro/AWS-compatible user-agent and bearer token headers.
- [ ] 3.2 Add Kiro generation client with endpoint fallback and request-budget integration.
- [ ] 3.3 Add AWS event-stream parser that emits text, reasoning, tool-use, usage, and error events.
- [ ] 3.4 Add Kiro error classification for auth, quota/rate-limit, transient, and unsupported payload failures.

## 4. Responses Translation And Dispatch

- [ ] 4.1 Add `ResponsesRequest` to Kiro payload translator for instructions, text, images, tools, tool results, and reasoning hints.
- [ ] 4.2 Force Kiro upstream `modelId` to `claude-sonnet-4.6` for every Kiro generation request.
- [ ] 4.3 Dispatch selected Kiro accounts through the Kiro adapter and selected OpenAI accounts through existing ChatGPT/Codex adapter.
- [ ] 4.4 Preserve streaming and non-streaming Responses output contracts for Kiro-backed requests.
- [ ] 4.5 Ensure `/v1/chat/completions` uses the same Kiro-backed Responses dispatch path.
- [ ] 4.6 Provide compatible compact behavior for Kiro-backed Codex clients without claiming real encrypted reasoning state.

## 5. Routing, Eligibility, And Logs

- [ ] 5.1 Keep OpenAI and Kiro accounts in one mixed load-balancing pool.
- [ ] 5.2 Preserve API-key account assignment, account exclusions, routing tiers, sticky affinity, cooldown, health, and failover behavior across providers where compatible.
- [ ] 5.3 Exclude Kiro accounts from audio transcription selection.
- [ ] 5.4 Record provider and upstream model information in request logs or equivalent observability output.

## 6. Verification

- [ ] 6.1 Add migration/account schema tests for provider defaults and Kiro credential fields.
- [ ] 6.2 Add Kiro import and token refresh unit tests.
- [ ] 6.3 Add Kiro translator/client/event-stream parser tests.
- [ ] 6.4 Add mixed-pool routing and endpoint eligibility tests.
- [ ] 6.5 Add proxy API tests for Kiro-backed streaming/non-streaming Responses and Chat Completions.
- [ ] 6.6 Run focused backend/frontend tests and `openspec validate --specs`.
