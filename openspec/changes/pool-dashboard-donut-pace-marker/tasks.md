## 1. Spec

- [x] 1.1 Specify that dashboard donut depletion markers use pooled weighted elapsed-window pace while risk severity remains worst-account based

## 2. Backend

- [x] 2.1 Add pooled weighted elapsed-window marker calculation with actual-capacity weighting and plan-multiplier fallback
- [x] 2.2 Thread pooled marker inputs through dashboard depletion aggregation without changing worst-account risk semantics

## 3. Tests

- [x] 3.1 Add unit tests for pooled weighting, multiplier fallback, and invalid-reset exclusion
- [x] 3.2 Add dashboard overview integration coverage for pooled marker behavior
