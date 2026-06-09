# 136 Runtime Lab Classifier Payload

## Scope

- Add a compact LLM payload for runtime-lab constrained intent arbitration.
- Exclude verbose candidate debug fields and enabled SOP lists from the LLM prompt payload.
- Preserve existing `to_dict()` response shape while allowing classifier debug metadata.

## Evidence

- `unit.txt`: `PYTHONPATH=. uv run pytest tests/unit/runtime_lab/test_constrained_classifier.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/domain/classifier.py tests/unit/runtime_lab/test_constrained_classifier.py`

## Result

PASS. Backend-only classifier payload contract is green; no browser UAT required.
