# 154 Customer Assistant Worker Profile Validation Gate

## User Story

As a demo operator configuring customer-assistant worker profiles, I need invalid worker/skill configuration to be rejected before it is persisted so a typo or empty policy reference cannot break a live MVP demo at runtime.

## Acceptance Criteria

1. PATCH `/api/v1/customer-assistant/worker-profiles/{profileId}` rejects unsupported `workerType` values.
2. PATCH rejects blank strategy/reference fields:
   - `modelPolicyRef`
   - `promptRef`
   - `toolPolicyRef`
   - `riskPolicyRef`
   - `outputSchemaRef`
3. PATCH rejects `toolRefs` containing blank values or duplicates.
4. Failed PATCH requests do not persist or partially merge invalid overrides.
5. Validation remains service-layer enforced so future API surfaces cannot bypass it.

## Out Of Scope

- Frontend profile editor UX.
- Dynamic worker plugin discovery.
- Runtime execution policy changes.
