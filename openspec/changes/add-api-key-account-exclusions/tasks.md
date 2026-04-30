## 1. OpenSpec and data model

- [ ] 1.1 Add OpenSpec proposal/design/spec/tasks for API-key account exclusions.
- [ ] 1.2 Add an Alembic migration for `api_key_accounts.assignment_type` with `allow` and `exclude` support.
- [ ] 1.3 Update ORM models and indexes/constraints for typed account policy rows.

## 2. Backend API-key contracts

- [ ] 2.1 Add backend schema/service/repository support for `excludedAccountIds`.
- [ ] 2.2 Add create-key account policy support for both allowed and excluded accounts.
- [ ] 2.3 Preserve update partial-field semantics so omitted account policy fields are unchanged.
- [ ] 2.4 Keep existing `assignedAccountIds` and `accountAssignmentScopeEnabled` compatibility.

## 3. Proxy enforcement

- [ ] 3.1 Enforce exclusions during normal account selection.
- [ ] 3.2 Enforce exclusions for preferred account reuse.
- [ ] 3.3 Enforce exclusions for HTTP bridge session/account reuse.

## 4. Frontend UX

- [ ] 4.1 Replace the account checkbox picker with a tri-state account policy picker.
- [ ] 4.2 Add the account policy picker to API-key create and edit dialogs.
- [ ] 4.3 Update Zod schemas, API types, mocks, and tests for `excludedAccountIds`.

## 5. Verification

- [ ] 5.1 Add focused backend unit and proxy tests for allow/exclude policy combinations.
- [ ] 5.2 Add frontend component/integration tests for create/edit tri-state payloads.
- [ ] 5.3 Run OpenSpec validation plus focused backend/frontend test suites.
