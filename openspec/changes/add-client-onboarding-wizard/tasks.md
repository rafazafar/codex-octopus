## 1. OpenSpec artifacts

- [x] 1.1 Add the `add-client-onboarding-wizard` proposal and frontend-architecture spec delta.

## 2. Frontend onboarding implementation

- [x] 2.1 Add an `Onboarding` route to the app shell and expose it in the main navigation.
- [x] 2.2 Implement onboarding config builders for Codex CLI, OpenCode, and generic OpenAI-compatible clients.
- [x] 2.3 Implement runtime-aware validation checks for readiness, model-list reachability, and auth mismatch guidance.

## 3. Verification

- [x] 3.1 Add focused onboarding builder tests and route integration tests.
- [x] 3.2 Update MSW mocks to cover onboarding reads and validation flows.
- [x] 3.3 Run OpenSpec validation and focused frontend verification.
