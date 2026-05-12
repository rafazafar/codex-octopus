## Why

Operators can delete selected sticky sessions, delete filtered sticky sessions, or purge stale prompt-cache mappings, but there is no explicit full-clear action. After routing-policy changes, operators may need to intentionally drop every sticky mapping so future requests can rebalance immediately.

## What Changes

- Add a dashboard "Purge All" action for sticky-session administration.
- Require confirmation before deleting all sticky-session mappings.
- Reuse the existing bulk deletion path so all sticky-session kinds are removed intentionally.

## Impact

- Affected spec: `sticky-session-operations`
- Affected frontend: sticky-session settings section and hook tests
