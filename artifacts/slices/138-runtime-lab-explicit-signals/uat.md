# 138 Runtime Lab Explicit Signals

## Scope

- Expand explicit handoff phrase detection.
- Let transactional SOP requests outrank background signals.
- Support described resume phrases for one suspended task.
- Avoid creating SOP candidates for airport facility FAQ-like questions.

## Evidence

- `unit.txt`: `PYTHONPATH=. uv run pytest tests/unit/runtime_lab/test_explicit_signals.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/domain/explicit_signals.py tests/unit/runtime_lab/test_explicit_signals.py`

## Result

PASS. Backend-only explicit signal detector contract is green; no browser UAT required.
