## Why

codex-lb already supports several client types, but successful setup still depends on reconstructing the right combination of README snippets, runtime assumptions, API-key expectations, and websocket notes. That creates avoidable first-run friction for operators and makes onboarding feel more like documentation assembly than product UX.

## What Changes

- Add a first-class dashboard `Onboarding` route for guided client setup.
- Generate environment-aware configuration for Codex CLI, OpenCode, and generic OpenAI-compatible clients using live dashboard/runtime facts.
- Add a validation panel that checks readiness, model-list reachability, and common auth/config mismatches with targeted remediation guidance.

## Capabilities

### Modified Capabilities

- `frontend-architecture`: add a dedicated onboarding surface in the dashboard shell for client setup and validation.

## Impact

- Affected frontend areas: app shell routing, top navigation, new onboarding feature slice, test mocks, and integration tests.
- Affected backend areas: none required for V1 beyond existing endpoints; the implementation reuses current settings, runtime connect-address, health, and model-list surfaces.
