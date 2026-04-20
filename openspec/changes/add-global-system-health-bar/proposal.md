## Why

Operators need a persistent cross-page warning surface for broad system-health problems such as account-pool collapse, imminent capacity exhaustion, or a sustained rate-limit wave. The current UI only has page-local alerts and a low-noise footer status bar, so major operational risk can be easy to miss unless the operator is already on the right page.

## What Changes

- add `GET /api/system-health` for shell-level operational risk summary
- add a persistent global incident bar on protected pages
- derive alerts from:
  - account availability
  - aggregate depletion risk
  - recent normalized request-log status mix

## Impact

- backend API contract addition
- small request-log aggregate addition
- app-shell UI addition
- frontend and backend test coverage updates
