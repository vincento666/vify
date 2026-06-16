# Plan: Runtime Lab SOP Chatflow V2 Binding & Resume Lifecycle

## Slice 105.1 Default Factory Runtime V2 Adapter And Resume

1. Add a RED unit contract to the Runtime Lab web factory tests.
2. Add a RED API E2E for Runtime Lab suspend/resume where a resumed runtime v2 Chatflow interrupts again.
3. Wire `ChatflowRuntimeV2Service` into `get_runtime_lab_service` when SOP Chatflow bindings exist.
4. Preserve interrupt state during runtime v2 resume so later node waits remain resumable.
5. Run focused unit, adapter integration, API E2E, runtime-v2, service, and lint regressions.
6. Add Browser UAT for the default configured Runtime Lab service using real Chatflow fixtures.
7. Update docs/evidence and commit the focused slice.

## Test Strategy

- Unit: `tests/unit/runtime_lab/test_runtime_lab_web_factory.py`
- Integration: `tests/integration/runtime_lab/test_chatflow_sop_runtime_adapter.py`
- API E2E: `tests/e2e/test_runtime_lab_chatflow_sop_api_e2e.py`
- Runtime v2 regression: `tests/integration/workflow/test_runtime_v2_node_coverage_pack1.py`, `tests/integration/workflow/test_chatflow_runtime_v2_facade.py`
- Runtime Lab service regression: `tests/integration/runtime_lab/test_runtime_lab_service.py`
- Browser UAT: `frontend/e2e/runtime-lab-sop-v2-binding.mjs`

## Risk Notes

- Factory tests inspect a private adapter field as a wiring contract; keep the assertion narrow and avoid runtime behavior assertions there.
- The default factory calls `get_settings()` directly, so the browser UAT will use environment-backed settings and a subprocess/dev server rather than FastAPI dependency overrides.
- Runtime Lab's configured scope only shows bound SOP scenarios; Browser UAT seeds both refund and invoice Chatflows so the interrupt/resume story is visible through the product UI.
- Existing live acceptance paths still need separate real-provider gates; this slice only ensures runtime v2 is the default SOP Chatflow execution path.
