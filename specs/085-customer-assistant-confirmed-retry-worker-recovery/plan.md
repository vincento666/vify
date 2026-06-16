# Plan 085

## 085.1 Confirmed Retry Worker Recovery

Implementation shape:

- Add a focused integration test in
  `tests/integration/customer_assistant/test_task_controls.py` that exercises
  the public task-control proposal and proposed-action confirmation APIs.
- Seed a failed deterministic `stub_qa` task in the test fixture so retry
  recovery can complete without browser or network dependencies.
- Reuse the existing ready-task dispatch path from `_act()` after
  `_confirm_proposed_task_command()` applies a retry/resume command.
- Keep confirmation events and proposed-action result payloads compatible while
  adding recovery evidence from the worker attempt.

TDD seams:

- RED: confirmed retry currently changes a failed task to `RUNNING` without
  `task_started`, `worker_started`, `task_completed`, or completed `lastResult`
  evidence.
- GREEN: confirmation dispatches the ready retry task and persists completed
  deterministic worker output.

Gates:

- `rtk uv run pytest tests/integration/customer_assistant/test_task_controls.py`
- `rtk uv run ruff check app/modules/customer_assistant/domain/service.py tests/integration/customer_assistant/test_task_controls.py`
- `rtk node --check frontend/e2e/customer-assistant-confirmed-retry-recovery.mjs`
- `rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:<port> node frontend/e2e/customer-assistant-confirmed-retry-recovery.mjs`

Browser UAT:

- Use a mocked browser UAT script to verify the visible workbench flow from
  failed task retry proposal through confirmed recovery state. No Vue/CSS
  changes are planned.
