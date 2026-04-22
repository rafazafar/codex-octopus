## MODIFIED Requirements

### Requirement: Dashboard page

The Dashboard page SHALL display summary metric cards for a selectable overview timeframe, primary and secondary usage donut charts with legends, account status cards grid, and a recent requests table with filtering and pagination. The donut safe-line marker MUST remain tied to the real quota window represented by each donut.

#### Scenario: Donut safe-line marker shows pooled on-pace progress

- **WHEN** the dashboard renders a primary or secondary quota donut for multiple visible accounts
- **THEN** `safeUsagePercent` for that donut reflects the pooled weighted elapsed progress across the accounts in that quota window
- **AND** actual quota capacity is used as the weight when available
- **AND** plan-type fallback weighting is used only when actual quota capacity is unavailable

#### Scenario: Depletion severity remains worst-account based

- **WHEN** the dashboard computes depletion details for a quota donut
- **THEN** the donut safe-line marker uses the pooled weighted elapsed progress for the window
- **AND** risk level, burn rate, and projected exhaustion remain derived from the most at-risk account in that window
