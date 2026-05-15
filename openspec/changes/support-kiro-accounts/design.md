## Context

codex-lb currently treats every stored account as a ChatGPT/Codex account. `Account` rows store OpenAI token material, `AccountsService.import_account()` normalizes OpenAI auth JSON, `ProxyService` decrypts the selected account access token, and `app.core.clients.proxy.stream_responses()` forwards to ChatGPT `/backend-api/codex/responses`.

Kiro-Go demonstrates the separate Kiro mechanics that codex-lb needs: Kiro account credentials include access token, refresh token, client id/secret, auth method, region, expiration, machine id, and optional profile ARN; Kiro generation calls use AWS/Kiro headers, Kiro endpoints, AWS binary event-stream parsing, OpenAI/Claude-to-Kiro payload conversion, and model alias mapping. Its OpenAI `/v1/chat/completions` implementation is the useful reference. Its `/backend-api/codex` endpoint is explicitly out of scope for reuse.

The user chose one mixed account pool with provider labels, not separate provider pools.

## Goals / Non-Goals

**Goals:**

- Keep OpenAI and Kiro accounts in one load-balancing pool.
- Label each account by provider in dashboard/API summaries.
- Support provider-aware account persistence and import.
- Route selected OpenAI accounts through existing ChatGPT upstream logic.
- Route selected Kiro accounts through native Kiro client/translator logic inside codex-lb.
- Force every Kiro generation request to `claude-sonnet-4.6`, regardless of the downstream requested model.
- Preserve API-key assignment, account exclusions, routing tiers, sticky affinity, request logs, and failover behavior across both providers where compatible.
- Keep transcription OpenAI-only.

**Non-Goals:**

- Reusing or forwarding to Kiro-Go as a required sidecar.
- Supporting Kiro-Go's native Codex-compatible endpoint.
- Making Kiro transcriptions work.
- Supporting multiple Kiro model targets in the first tranche.
- Changing public client endpoints or requiring clients to know the selected provider.

## Decisions

1. Store provider type on the account row.

   Rationale: provider decides credential shape, refresh logic, upstream headers, eligible endpoints, and dashboard labels. Keeping provider on the account makes the mixed pool explicit and avoids guessing from token fields.

2. Add Kiro credential metadata as provider-specific account fields.

   Rationale: Kiro refresh requires client id/secret, auth method, region, refresh token, and token expiration. A JSON credential blob would reduce migrations, but typed fields are easier to validate, redact, display, test, and migrate safely.

3. Use one load-balancer pool with provider eligibility filters.

   Rationale: the user's intent is "mix same pool as chatgpt accounts, just labeled." Shared routing preserves API-key assignments, tiers, sticky mappings, health/cooldown behavior, and request logs. Endpoint-specific filters only remove incompatible providers, such as Kiro for transcription.

4. Dispatch after account selection.

   Rationale: most routing decisions do not care about provider. Once an account is selected, `ProxyService` can branch to `openai` or `kiro` upstream adapters. This keeps selection behavior centralized and keeps Kiro specifics out of the balancer.

5. Translate from codex-lb internal Responses requests to Kiro payloads.

   Rationale: `/v1/chat/completions` already maps to `ResponsesRequest`; `/backend-api/codex/responses` and `/v1/responses` already enter the Responses path. Translating at this boundary gives one Kiro implementation for chat, Responses, and Codex-compatible clients.

6. Force Kiro model to `claude-sonnet-4.6`.

   Rationale: the desired behavior is provider mapping, not user-selectable Kiro model routing. The public response should continue reporting the requested downstream model unless existing compatibility rules require otherwise; request logs should include enough provider/upstream detail to show Kiro actually used Claude Sonnet 4.6.

7. Return synthetic compact compatibility for Kiro if needed by Codex clients.

   Rationale: Kiro does not expose OpenAI encrypted reasoning state. A minimal compatible compact response is safer than breaking Codex clients that expect a compact endpoint, as long as the system does not claim real encrypted-state preservation.

## Data Model

Add `accounts.provider` with default `openai`. Add Kiro fields for:

- `kiro_auth_method`
- `kiro_client_id_encrypted`
- `kiro_client_secret_encrypted`
- `kiro_region`
- `kiro_expires_at`
- `kiro_machine_id`
- `kiro_profile_arn`
- optional `kiro_provider`

Reuse encrypted access/refresh token fields for both providers because both are bearer/refresh token pairs. Keep `id_token_encrypted` nullable or provider-compatible so Kiro accounts do not need fabricated OpenAI id tokens.

Provider labels should surface through `AccountSummary.provider`. Existing account imports default to `openai`.

## Request Flow

1. Public route validates API key and request as today.
2. Chat requests map to `ResponsesRequest` as today.
3. Proxy service selects an eligible account from the mixed pool.
4. If provider is `openai`, existing ChatGPT/Codex upstream code runs.
5. If provider is `kiro`, Kiro token freshness is checked and refreshed when needed.
6. The Responses request is translated to a Kiro payload with `modelId` forced to `claude-sonnet-4.6`.
7. The Kiro client sends the request to configured Kiro/CodeWhisperer/AmazonQ endpoints with safe fallback semantics.
8. AWS event-stream frames become existing Responses SSE events or collected non-streaming payloads.
9. Request logs record selected account, requested model, provider, upstream model, usage, status, and error detail.

## Error Handling

- Kiro auth refresh failures map to authentication errors and may deactivate or mark the account according to existing permanent-failure patterns.
- Kiro 429/quota-style failures mark only the selected Kiro account and allow failover to another eligible account when the request has not committed output.
- Kiro 5xx/network failures use existing transient failure/circuit-breaker behavior where possible.
- Unsupported Kiro request features produce stable OpenAI `invalid_request_error` envelopes.
- Transcription with no eligible OpenAI accounts returns `no_compatible_accounts` or equivalent stable selection error.

## Testing

- Migration/model tests for provider defaults and nullable Kiro fields.
- Account import tests for OpenAI default behavior and Kiro credential import.
- Mixed-pool load-balancer tests proving OpenAI and Kiro accounts share routing, assignment, and tier behavior.
- Provider eligibility tests proving transcription excludes Kiro.
- Kiro auth refresh tests for OIDC and social refresh flows.
- Kiro payload translator tests for text, images, tools, tool results, system instructions, reasoning/thinking hints, and forced `claude-sonnet-4.6`.
- Kiro event-stream parser tests for text deltas, reasoning deltas, tool use, usage, quota, and malformed frames.
- Proxy API tests for streaming and non-streaming Kiro-backed Responses plus Chat Completions.

## Rollout

1. Add schema fields and OpenAI default provider.
2. Add provider labels to account APIs without changing selection.
3. Add Kiro import and refresh primitives behind tests.
4. Add Kiro translator/client and dispatch branch.
5. Add endpoint eligibility filters and request-log provider/upstream model fields.
6. Expose dashboard Kiro import affordance and provider labels.
7. Validate OpenSpec and focused backend/frontend tests before archive.
