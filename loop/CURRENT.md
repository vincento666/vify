# Current Loop Scope: Unified Runtime V2 and Workflow/Chatflow Branch

## Status

    mode: Closed Loop
    operation: full-history branch integration and regression verification
    source branch: codex/runtime-v2-production-upgrade (9 commits)
    integration branch: codex/unify-runtime-v2-spec-222

No new product slice is open in this integration. The merge must retain both
independent Spec-225 records; their numeric collision is documented by their
stable directory names rather than by renaming either historical directory.

## Preserved Contract Records

- `specs/225-workflow-chatflow-control-hardening/` records Workflow/Chatflow
  control hardening: browser geometry, structured-row reorder, panel controls,
  lifecycle/variable scope, Runtime V2 Intent binding, and the bounded live
  provider matrix. Its evidence remains under
  `artifacts/slices/225-workflow-chatflow-control-hardening/`.
- `specs/225-runtime-lab-sop-live-stream/` records the RuntimeLab SOP bridge:
  genuine Provider deltas over Runtime V2, Customer Assistant compatibility,
  in-process parallel LLM/Knowledge/safe-Tool waves, timeout/failure fencing,
  and Redis/outbox read-side sequence recovery. Its evidence remains under
  `artifacts/slices/225-runtime-lab-sop-live-stream/`.
- AI Assistant memory and model-usage work is included with Alembic revisions
  `0032_ai_assistant_memory_scope`, `0033_ai_assistant_memory_cursor`, and
  `0034_ai_assistant_model_usage`.

## Integration Boundaries

- The integration imports the authorized commits and migrations; it does not
  apply migrations to a deployed database.
- No credentials, live-provider calls, or external spend are needed for this
  merge verification.
- The original worktree's uncommitted changes are outside this merge commit and
  must be stashed and restored only after the clean integration is verified.

## Next Action

Run combined backend/frontend/migration regression gates, inspect the merge
diff, commit the integration, then fast-forward the original worktree and
restore its uncommitted changes.
