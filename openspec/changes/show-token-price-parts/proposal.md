# show-token-price-parts

## Why

Request history currently shows total tokens plus cached input tokens, but pricing is calculated from three separate parts: billable input, cached input, and output. Operators need the display to make that split explicit so token totals and cost totals are easier to reconcile.

## What Changes

- Expose input, billable input, cached input, and output token parts on request-log entries.
- Expose the same token split on API-key usage summaries and 7-day usage payloads.
- Update the shared request-history table used by Dashboard and API-key history to show the token split.
- Update API-key summary surfaces to use the same split.

## Impact

- No database migration is required; the values are derived from existing request-log token fields.
- Existing total token and cost fields remain available.
