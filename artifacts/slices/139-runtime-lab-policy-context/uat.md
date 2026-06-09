# 139 Runtime Lab Policy Context

## Scope

- Add active-task continuation guardrails and suspended-task switch protection.
- Add recent-completed duplicate confirmation protection.
- Preserve and inherit business context across related SOP starts/resumes.
- Let deterministic fallback recover from LLM classifier failures when possible.
- Pass inherited collected values through the fake SOP adapter path.

## Evidence

- `integration.txt`: `PYTHONPATH=. uv run pytest tests/integration/runtime_lab/test_runtime_lab_service.py tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py tests/integration/runtime_lab/test_runtime_lab_reliability.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/domain/service.py app/modules/runtime_lab/domain/policy.py app/modules/runtime_lab/domain/sop.py app/modules/runtime_lab/domain/sop_adapter.py tests/integration/runtime_lab/test_runtime_lab_service.py tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py tests/integration/runtime_lab/test_runtime_lab_reliability.py`

## Result

PASS. Runtime-lab policy/context integration is green; no browser UAT required.
