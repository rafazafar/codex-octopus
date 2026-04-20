## 1. OpenSpec artifacts

- [x] 1.1 Add the `add-client-onboarding-wizard` proposal and frontend-architecture spec delta.

## 2. Frontend onboarding implementation

- [x] 2.1 Add an `Onboarding` route to the app shell and expose it in the main navigation.
- [x] 2.2 Implement onboarding config builders for Codex CLI, OpenCode, and generic OpenAI-compatible clients.
- [x] 2.3 Implement runtime-aware validation checks for readiness, model-list reachability, and auth mismatch guidance.
- [x] 2.4 Make `/onboarding` publicly reachable without relaxing the rest of the dashboard auth gate.
- [x] 2.5 Split onboarding bootstrap reads to a minimal public contract and keep anonymous onboarding view-only.

## 3. Backend public bootstrap implementation

- [x] 3.1 Add a minimal anonymous onboarding bootstrap endpoint that exposes only connect-address guidance and API-key-auth state.
- [x] 3.2 Keep `/api/settings` and other existing dashboard routes protected.

## 4. Verification

- [x] 4.1 Add focused onboarding builder tests and route integration tests.
- [x] 4.2 Update MSW mocks to cover onboarding reads and validation flows.
- [x] 4.3 Add backend verification for the public onboarding endpoint and protected settings routes.
- [x] 4.4 Run OpenSpec validation and focused frontend/backend verification.
