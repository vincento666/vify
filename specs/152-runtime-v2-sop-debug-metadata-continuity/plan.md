# Plan: 152.1 Runtime V2 Debug Metadata Continuity

## Slice

Make runtime v2 durable events carry minimal caller and version debug metadata
throughout the run lifecycle.

1. Add RED shared-core assertions for caller context on node/status/completed
   events.
2. Add RED published-version assertions for version metadata on node/completed
   and resume lifecycle events.
3. Inject run-level debug metadata in `_append_event` from persisted run input.
4. Keep payload compact by adding only `callerContext`, `definitionSource`,
   `versionId`, and `version`.
5. Run focused integration and ruff gates.

## Verification

- `rtk env PYTHONPATH=. uv run pytest tests/integration/workflow/test_runtime_v2_shared_core.py`
- `rtk env PYTHONPATH=. uv run pytest tests/integration/workflow/test_runtime_v2_published_version_targeting.py`
- `rtk env PYTHONPATH=. uv run ruff check app/modules/workflow/domain/runtime_v2.py tests/integration/workflow/test_runtime_v2_shared_core.py tests/integration/workflow/test_runtime_v2_published_version_targeting.py`

## Result

Completed. Final evidence is saved under
`artifacts/slices/152-runtime-v2-sop-debug-metadata-continuity/152.1/`.
