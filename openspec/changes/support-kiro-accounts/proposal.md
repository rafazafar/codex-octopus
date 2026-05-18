## Why

Operators want codex-lb to route requests across both ChatGPT/Codex accounts and Kiro accounts from one account pool. Today account storage, refresh, upstream headers, and proxy forwarding are ChatGPT-shaped, so Kiro credentials cannot participate in normal routing or API-key assignment. Kiro-Go proves the Kiro upstream can serve OpenAI-compatible chat traffic by translating requests into Kiro payloads and mapping model aliases to Claude models, but its native Codex endpoint is not reliable enough to reuse directly.

## What Changes

- Add provider-aware account records with `openai` and `kiro` providers while keeping one mixed load-balancing pool.
- Label provider type in dashboard account summaries so operators can distinguish ChatGPT and Kiro accounts without managing separate pools.
- Add Kiro account import/storage fields for access tokens, refresh tokens, client metadata, expiration, machine id, and profile ARN.
- Add a Kiro upstream client that refreshes Kiro credentials, builds Kiro/AWS-compatible headers, sends Kiro generation requests, parses AWS event-stream responses, and maps errors into OpenAI envelopes.
- Route selected Kiro accounts through a Responses-to-Kiro translation path that forces all Kiro generation requests to `claude-sonnet-4.6`.
- Preserve existing ChatGPT/Codex behavior for OpenAI accounts.
- Keep audio transcription OpenAI-only and return a clear no-compatible-account error when only Kiro accounts are eligible.

## Capabilities

### New Capabilities

- `account-providers`: Provider-aware account identity, import, mixed-pool routing, Kiro credential refresh, and Kiro upstream dispatch.

### Modified Capabilities

- `responses-api-compat`: Responses and Codex-compatible requests can be served by Kiro accounts through translated Kiro generation calls.
- `chat-completions-compat`: Chat Completions continues to map through Responses, including Kiro-account dispatch.
- `audio-transcriptions-compat`: Transcription requests remain restricted to OpenAI/ChatGPT accounts.
- `frontend-architecture`: Account views show provider labels and support Kiro account onboarding/import affordances.

## Impact

- Affected backend areas: account schema and migrations, account import/export, auth refresh, load balancer account state, proxy service dispatch, upstream clients, request logging, model/access validation, usage refresh, and health checks.
- Affected frontend areas: Accounts page labels and Kiro account import/add controls.
- Affected verification: OpenSpec validation, account import tests, load-balancer mixed-pool tests, Kiro translator/client unit tests, proxy streaming/non-streaming tests, chat-completions Kiro dispatch tests, and transcription provider-filter tests.
