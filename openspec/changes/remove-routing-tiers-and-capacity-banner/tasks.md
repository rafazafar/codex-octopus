## 1. Backend Routing Tier Removal

- [x] 1.1 Remove routing-tier request/response types from account schemas.
- [x] 1.2 Remove the account routing-tier update route, service method, and repository method.
- [x] 1.3 Remove routing-tier fields from account summary mapping.
- [x] 1.4 Remove routing-tier weights from settings parsing and capacity-weighted balancer calls.
- [x] 1.5 Remove routing-tier weighting logic from balancer selection.

## 2. Frontend Removal

- [x] 2.1 Remove routing-tier fields, types, API calls, hooks, mocks, and UI labels/controls.
- [x] 2.2 Remove the global incident banner from shell layout composition and tests.
- [x] 2.3 Keep page-local system-health behavior only where still reachable without the shell banner.

## 3. Tests and Validation

- [x] 3.1 Remove or update backend tests covering removed routing-tier APIs and weighting.
- [x] 3.2 Remove or update frontend tests covering removed routing-tier controls and banner rendering.
- [x] 3.3 Run targeted backend, frontend, and OpenSpec validation.
