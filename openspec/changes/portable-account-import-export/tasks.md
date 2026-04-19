## 1. OpenSpec and account-transfer models

- [x] 1.1 Add the `account-portability` proposal/spec/design artifacts for portable import/export behavior.
- [x] 1.2 Introduce typed portable-account parsing/export models and format detection for current auth JSON vs external portable JSON.

## 2. Backend import/export implementation

- [x] 2.1 Refactor account persistence to support caller-owned transactions for batch imports without changing current merge-vs-duplicate rules.
- [x] 2.2 Update `POST /api/accounts/import` to normalize one or many records, validate the full payload, persist atomically, and return an import summary response.
- [x] 2.3 Add `GET /api/accounts/export` to serialize all stored accounts as an external portable JSON attachment.

## 3. Frontend account portability UX

- [x] 3.1 Update frontend account schemas and API client code for the new import summary response and export download endpoint.
- [x] 3.2 Update the Accounts dashboard UI copy/actions to support multi-format import and portable export with sensitive-file wording.

## 4. Verification

- [x] 4.1 Add backend tests for current-format import, portable-array import, rollback-on-invalid batch, setting-driven conflict handling, and portable export round-trips.
- [x] 4.2 Add frontend tests/mocks for import dialog copy, export action wiring, and new API endpoints.
- [x] 4.3 Run OpenSpec validation plus focused backend/frontend test suites covering the new portability flow.
