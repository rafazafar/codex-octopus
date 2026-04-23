## 1. OpenSpec and data model

- [ ] 1.1 Add the `account-expiry` proposal/spec/design artifacts for account-level expiry behavior.
- [ ] 1.2 Add database support for nullable `accounts.expires_at`.

## 2. Backend expiry behavior

- [ ] 2.1 Add expiry to account schemas, mappers, and repository update paths.
- [ ] 2.2 Default expiry to 30 days on add/import when the incoming payload has no expiry, and preserve payload expiry when provided.
- [ ] 2.3 Add portable import/export support for expiry round-tripping.
- [ ] 2.4 Exclude expired accounts from normal selection/routing without mutating lifecycle `status`.
- [ ] 2.5 Add `PATCH /api/accounts/{account_id}/expiry` for set/extend/clear operations.

## 3. Frontend account expiry UX

- [ ] 3.1 Update frontend account schemas and hooks for `expiresAt` and `isExpired`.
- [ ] 3.2 Show expiry state in the Accounts list/detail surfaces.
- [ ] 3.3 Add a manual expiry editing flow in the account detail view.

## 4. Verification

- [ ] 4.1 Add backend tests for default expiry, portable preserve/reset behavior, manual update, and routing exclusion.
- [ ] 4.2 Add frontend tests for expiry rendering and edit actions.
- [ ] 4.3 Run OpenSpec validation plus focused backend/frontend suites covering account expiry behavior.
