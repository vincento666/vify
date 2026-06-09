# 140 Runtime Lab Chatflow SOP Adapter

## Scope

- Normalize unexpected chatflow runtime failures into failed SOP results.
- Pass inherited context, conversation history, and collected business values into chatflow runtime input.
- Extract order, phone, passenger, route, and target time from Chinese booking/change-flight messages and final replies.
- Let current-turn values override stale inherited chatflow session variables.

## Evidence

- `integration.txt`: `PYTHONPATH=. uv run pytest tests/integration/runtime_lab/test_chatflow_sop_runtime_adapter.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/domain/chatflow_adapter.py tests/integration/runtime_lab/test_chatflow_sop_runtime_adapter.py`

## Result

PASS. Runtime-lab chatflow SOP adapter integration is green; no browser UAT required.
