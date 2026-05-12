## 1. Spec And Data Model

- [x] 1.1 Add account routing tier persistence with backward-compatible bronze behavior for existing or missing values.
- [x] 1.2 Add runtime configuration for `gold`, `silver`, and `bronze` tier weights with safe defaults and fallback for invalid entries.

## 2. Routing Implementation

- [x] 2.1 Carry normalized account routing tier from account rows into `AccountState`.
- [x] 2.2 Apply tier weights inside `capacity_weighted` selection by multiplying remaining secondary capacity by the normalized tier weight.
- [x] 2.3 Preserve existing eligibility, health-tier, sticky-affinity, and fallback behavior.

## 3. Verification

- [x] 3.1 Add focused tests proving gold/silver/bronze weighted-share distribution with configurable weights.
- [x] 3.2 Add focused tests proving missing, empty, or unknown account tiers use bronze behavior and remain routable.
- [x] 3.3 Run focused balancer/database tests and OpenSpec validation.
