# 029.7 Runtime-lab API UAT

## Scope

Backend API UAT only. Spec 029 has no frontend/browser/rem gate.

## Request Flow

1. `POST /api/v1/runtime-lab/sessions`
   - Result: creates `ACTIVE` runtime-lab session.
2. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `我要退票`
   - Result: `START_SOP`, active task `refund_ticket`, step `collect_order_no`.
3. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `我要开发票`
   - Result: `SUSPEND_AND_START`, suspended task `refund_ticket`, active task `invoice_apply`.
4. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `INV-200`
   - Result: `CONTINUE_ACTIVE_SOP`, active task `invoice_apply`, step `confirm`.
5. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `确认`
   - Result: `COMPLETE_TASK`, invoice task completed, `resumeOffer.sopId=refund_ticket`.
6. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `继续刚才`
   - Result: `RESUME_TASK`, active task restored to `refund_ticket`, step `collect_order_no`.
7. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `TK-100`
   - Result: `CONTINUE_ACTIVE_SOP`, refund task step `confirm`.
8. `POST /api/v1/runtime-lab/sessions/{id}/messages` with `我要改签`
   - Result: `REJECT_SWITCH_CONTINUE_ACTIVE`, no new task created.

## Evidence

- API E2E command: `PYTHONPATH=. uv run pytest tests/e2e/test_runtime_lab_api_e2e.py`
- Result saved in `e2e.txt`.
- Reliability command: `PYTHONPATH=. uv run pytest tests/integration/runtime_lab/test_runtime_lab_reliability.py`
- Result saved in `reliability.txt`.
- Full backend command: `PYTHONPATH=. uv run pytest`
- Result saved in `full-pytest.txt`: `325 passed, 4 skipped, 1 warning`.
