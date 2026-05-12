## 1. Spec

- [x] 1.1 Add sticky-session purge-all dashboard requirement.

## 2. Implementation

- [x] 2.1 Add a hook mutation for deleting all sticky sessions.
- [x] 2.2 Add a confirmed "Purge All" button to the Settings sticky-session section.
- [x] 2.3 Delete filtered sticky-session sets with a filter-level database delete instead of per-row predicates.

## 3. Verification

- [x] 3.1 Add/update frontend tests for the purge-all workflow.
- [x] 3.2 Run focused sticky-session frontend tests and OpenSpec validation.
- [x] 3.3 Add/update backend coverage for large sticky-session purge sets.
