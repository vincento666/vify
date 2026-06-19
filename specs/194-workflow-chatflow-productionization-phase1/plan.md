# Plan 194: Workflow/Chatflow Productionization Phase 1

## Architecture Approach

1. Keep the shared Workflow/Chatflow runtime v2 core as the only default production execution path.
2. Add missing node executors and governance by reusing existing legacy engine helpers where they already model compatible behavior, then normalize their output into runtime v2 node events/evidence.
3. Route all recoverable node errors through a single policy resolver:
   - `fail`: terminal node/run failure.
   - `continue`: expose sanitized error output and continue on default outlet.
   - `branch`: route to error outlet and require that outlet during run/publish validation.
4. Bind runtime v2 services to immutable run snapshots. Resolver setup must use the snapshot carried by the run definition, not the current editable draft.
5. Keep UI clean and low-copy. For phase 1, add/edit only fields that directly map to runtime/validation/evidence.
6. Save evidence under `artifacts/slices/194-workflow-chatflow-productionization-phase1/{slice}/`.

## Parallel Work Allocation

- Backend runtime worker: 194.1 and executor plumbing for API/Tool/LLM-tools.
- Backend validation/version worker: 194.2, 194.4, and 194.5 server-side checks.
- Frontend governance/evidence worker: 194.3, 194.5 UI-side fields/errors, and 194.6 debug evidence projection.
- Main agent: merge changes, resolve conflicts, run gates, produce final UAT/node report.

## Test Strategy

- RED first for every slice and save output in the slice artifact directory.
- Backend unit:
  - `tests/unit/workflow/test_runtime_v2_core.py`
  - `tests/unit/workflow/test_publish_validation.py`
  - new focused policy/validation tests as needed.
- Backend integration:
  - runtime v2 API/Tool/LLM/Agent/Execute Workflow focused tests under `tests/integration/workflow/`.
  - existing Workflow/Chatflow/SOP compatibility tests must remain green.
- Contract:
  - publish/runtime/version API contracts when response shape changes.
- Frontend unit/rem:
  - `frontend/src/views/workflow/*` focused tests.
  - `frontend/src/remScaleClosure.test.ts`.
- E2E/UAT:
  - focused workflow/chatflow runtime v2 UAT scripts with screenshots.

## Risk Controls

- Do not modify unrelated customer-assistant or AI-assistant files unless the runtime v2 integration directly requires it.
- Do not remove legacy endpoints or response shapes.
- If a node cannot be made production-safe in one slice, block run/publish with a precise error instead of silently falling back.
- Treat dirty worktree files as existing work; preserve unrelated user changes.
