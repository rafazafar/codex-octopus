## Why

Accounts can remain stored as `active` after their access token expires when no usable refresh token is present. That lets routing choose accounts that can only fail upstream.

## What Changes

- Add a periodic account auth-health check.
- Deactivate non-paused, non-deactivated accounts whose access token is expired or near expiry and whose refresh token is missing.
- Proactively refresh accounts whose access token is expired or near expiry and whose refresh token is present.
- Keep transient refresh failures non-destructive while allowing permanent refresh failures to deactivate through existing auth-manager behavior.

## Impact

- Affected code: account auth manager, background schedulers, app startup.
- Affected operators: accounts requiring re-login are marked before normal routing selects them.
