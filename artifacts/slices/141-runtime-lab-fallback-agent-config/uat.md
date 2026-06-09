# 141 Runtime Lab Fallback Agent Config

## Scope

- Expose current fallback Agent config and selectable enabled Agent options in runtime-lab config.
- Add `/api/v1/runtime-lab/fallback-agent` to select or disable an existing Agent fallback.
- Wire runtime-lab service construction to use the selected existing Agent fallback.
- Keep arbitrator API keys hidden and avoid 500s when LLM arbitrator keys are missing.

## Evidence

- `contract.txt`: `PYTHONPATH=. uv run pytest tests/contract/test_runtime_lab_config_api.py tests/unit/runtime_lab/test_runtime_lab_web_factory.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/web/router.py app/modules/runtime_lab/web/schemas.py tests/contract/test_runtime_lab_config_api.py tests/unit/runtime_lab/test_runtime_lab_web_factory.py`

## Result

PASS. Runtime-lab fallback Agent config API contract is green; no browser UAT required for this backend slice.
