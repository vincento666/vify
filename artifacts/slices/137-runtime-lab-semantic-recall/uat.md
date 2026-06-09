# 137 Runtime Lab Semantic Recall

## Scope

- Strengthen mock semantic recall for airline SOP routing.
- Prefer active task continuation only when the message looks like collection detail.
- Add weak booking/refund signals while avoiding airport facility FAQ-like messages.
- Keep obvious new business requests from being swallowed by an active SOP candidate.

## Evidence

- `unit.txt`: `PYTHONPATH=. uv run pytest tests/unit/runtime_lab/test_mock_semantic_recall.py -q`
- `ruff`: `uv run ruff check app/modules/runtime_lab/domain/recall.py tests/unit/runtime_lab/test_mock_semantic_recall.py`

## Result

PASS. Backend-only semantic recall contract is green; no browser UAT required.
