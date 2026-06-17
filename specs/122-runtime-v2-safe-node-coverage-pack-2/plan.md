# Implementation Plan: Runtime V2 Safe Node Coverage Pack 2

## Status

Complete.

## Approach

1. Inspect current runtime-v2 node dispatch, event model, checkpoint model, and
   lifecycle tests.
2. Add focused RED coverage for `EXECUTE_WORKFLOW` and `TRANSFER_TO_HUMAN` using
   the existing runtime-v2 test style.
3. Implement only the missing safe behavior in the workflow runtime/domain
   layer.
4. Run focused tests first, then the local runtime-v2 regression set and `ruff`.
5. Record RED/green evidence and update this plan with final results.

## Design Notes

- `EXECUTE_WORKFLOW` will stay side-effect free in this slice. It should provide
  deterministic child-run evidence instead of invoking persisted workflows.
- `TRANSFER_TO_HUMAN` should use the runtime's existing pause/resume machinery
  if available. If the current runtime vocabulary exposes a more specific
  handoff event, the implementation should prefer that vocabulary.
- Unknown node behavior must not become permissive as a side effect of adding
  coverage for these node types.

## Validation Commands

- RED:
  `rtk uv run pytest tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py`
- Focused:
  `rtk uv run pytest tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py`
- Regression:
  `rtk uv run pytest tests/unit/workflow/test_runtime_v2_core.py tests/integration/workflow/test_runtime_v2_node_coverage_pack1.py tests/integration/workflow/test_runtime_v2_shared_core.py tests/integration/workflow/test_runtime_v2_long_run_lifecycle.py tests/integration/workflow/test_chatflow_runtime_v2_facade.py tests/integration/workflow/test_workflow_runtime_v2_facade.py tests/integration/workflow/test_runtime_v2_published_version_targeting.py tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py`
- Ruff:
  `rtk uv run ruff check app/modules/workflow/domain/runtime_v2.py tests/integration/workflow/test_runtime_v2_safe_node_coverage_pack2.py`

## Evidence

- RED: `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/red.txt`
- Focused: `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/focused.txt`
- Regression:
  `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/runtime-v2-regression.txt`
- Ruff: `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/ruff.txt`
- Browser UAT:
  `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/uat.md`
