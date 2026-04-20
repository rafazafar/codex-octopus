## 1. OpenSpec
- [ ] 1.1 Add proposal, design, and tasks for `add-global-system-health-bar`
- [ ] 1.2 Add frontend-architecture delta for the global incident bar
- [ ] 1.3 Add proxy-runtime-observability delta for system-health summary alerts

## 2. Backend
- [ ] 2.1 Add `app/modules/system_health/schemas.py`
- [ ] 2.2 Add `app/modules/system_health/repository.py`
- [ ] 2.3 Add `app/modules/system_health/service.py`
- [ ] 2.4 Add `app/modules/system_health/api.py`
- [ ] 2.5 Add dependency wiring in `app/dependencies.py`
- [ ] 2.6 Register the router in `app/main.py`
- [ ] 2.7 Add recent normalized request-log status-count aggregate in `app/modules/request_logs/repository.py`

## 3. Frontend
- [ ] 3.1 Add `frontend/src/features/system-health/schemas.ts`
- [ ] 3.2 Add `frontend/src/features/system-health/api.ts`
- [ ] 3.3 Add `frontend/src/features/system-health/hooks/use-system-health.ts`
- [ ] 3.4 Add `frontend/src/components/layout/global-incident-bar.tsx`
- [ ] 3.5 Mount the incident bar in `frontend/src/App.tsx`

## 4. Tests
- [ ] 4.1 Add backend integration coverage for `GET /api/system-health`
- [ ] 4.2 Add backend rule tests for account-pool, depletion, and rate-limit alerts
- [ ] 4.3 Add frontend MSW handlers/factories for system-health responses
- [ ] 4.4 Add frontend hook tests for polling and healthy/error states
- [ ] 4.5 Add frontend layout/component tests for protected-route rendering

## 5. Validation
- [ ] 5.1 Run OpenSpec validation
- [ ] 5.2 Run focused backend integration tests
- [ ] 5.3 Run focused frontend vitest coverage
