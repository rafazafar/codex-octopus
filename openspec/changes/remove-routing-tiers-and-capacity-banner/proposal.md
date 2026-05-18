## Why

The recently added account routing tier system adds operator-facing controls and routing weight behavior that are no longer wanted. The global capacity alert/banner also adds noise in the shell UI and should no longer interrupt operators.

## What Changes

- **BREAKING** Remove the account routing tier API contract, including `gold`, `silver`, `bronze`, and default tier semantics.
- Remove routing-tier weighting from capacity-weighted account selection.
- Remove routing-tier controls and labels from the accounts UI.
- Remove routing-tier configuration parsing and tests.
- Remove the global capacity/system-health banner from the application shell.
- Keep the underlying system-health endpoint available unless no remaining code needs it.
- Keep existing database columns unless a later cleanup explicitly removes persisted schema.

## Capabilities

### New Capabilities

- `account-management`: Account management API and routing behavior after routing-tier removal.

### Modified Capabilities

- `frontend-architecture`: Accounts UI no longer exposes routing tiers, and the app shell no longer renders the global system-health incident banner.

## Impact

- Backend account schemas, account API routes, account repository/service code, and account mappers.
- Capacity-weighted load-balancer logic and proxy account-state construction.
- Settings parsing for account routing tier weights.
- Frontend account list/detail components, account hooks/API types, mocks, and tests.
- Layout-level global incident banner component and tests.
