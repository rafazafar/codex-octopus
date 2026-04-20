## Why

codex-lb already supports several client types, but successful setup still depends on reconstructing the right combination of README snippets, runtime assumptions, API-key expectations, and websocket notes. That creates avoidable first-run friction for operators and makes onboarding feel more like documentation assembly than product UX.

## What Changes

- Add a first-class dashboard `Onboarding` route for guided client setup.
- Generate environment-aware configuration for Codex CLI, OpenCode, and generic OpenAI-compatible clients using live dashboard/runtime facts.
- Add a validation panel that checks readiness, model-list reachability, and common auth/config mismatches with targeted remediation guidance.
- Make `/onboarding` publicly reachable with a minimal anonymous bootstrap contract instead of reusing the private settings API.
- Keep anonymous onboarding view-only while preserving richer validation for authenticated dashboard sessions.

## Capabilities

### Modified Capabilities

- `frontend-architecture`: add a dedicated onboarding surface in the dashboard shell for client setup and validation.

## Impact

- Affected frontend areas: app shell routing, top navigation, new onboarding feature slice, test mocks, and integration tests.
- Affected backend areas: add a minimal public onboarding bootstrap endpoint while keeping existing settings routes protected.
