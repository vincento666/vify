# 187.1 Scheduler Backend Slice Summary

## Modification Scope

- `app/modules/ai_assistant/domain/scheduler.py`
- `app/modules/ai_assistant/domain/harness.py`
- `app/modules/ai_assistant/web/schemas.py`
- `app/modules/ai_assistant/web/router.py`
- `tests/unit/ai_assistant/test_tool_scheduler.py`
- `tests/integration/ai_assistant/test_tool_scheduler_metadata.py`
- `tests/contract/test_ai_assistant_scheduler_api.py`
- `specs/187-ai-assistant-tool-scheduler-rwmutex/*`

No frontend visual files changed. Existing dirty `customer_assistant` files were
not part of this slice.

## RED Evidence

- `red-unit.txt`: scheduler module missing before implementation.
- `red-contract.txt`: API ignored `toolCalls[]` and returned only one default
  `echo_context` result before scheduler API support.

## Implementation Summary

- Added deterministic tool scheduler planning for read-only parallel batches,
  write-exclusive batches, and unresolved-resource serial fallback.
- Added resource template resolution for manifest resources such as
  `session:{session_id}` and `customer:{customerId}`.
- Added scheduler metadata:
  `schedulerBatchId`, `schedulerPosition`, `lockMode`, `readResourceKeys`,
  `writeResourceKeys`, `resourceLockReason`, and `parallelEligible`.
- Added backend-only `toolCalls[]` request support while preserving the 184
  single-tool request contract.
- Added bounded parallel dispatch for compatible read-only batches; persistence
  remains deterministic in planned order.
- Persisted scheduler metadata through MySQL8 JSON payloads on tool calls and
  scheduler/tool events.

## Gates Run

- Unit: `unit-scheduler.txt`
- MySQL8 integration: `integration-mysql8.txt`, `metadata-gates.txt`
- Contract: `contract.txt`, `contract-regression.txt`
- E2E regression: `e2e.txt`
- Ruff: `ruff.txt`
- Mypy: `mypy.txt`
- MySQL8 boundary scan: `mysql8-boundary-scan.txt`

Frontend unit, `remScaleClosure`, and browser UAT are not applicable to this
backend-only slice because no frontend visual files changed.

## Remaining Risks

- Phase 4 durable lock rows and cross-process lock contention are not
  implemented; this slice stores scheduler metadata and deterministic in-process
  decisions only.
- Business writes still stop at the existing 184 approval/proposed-action
  boundary and do not execute real mutations.
- Real LLM planning is deferred; future optional live probes must use
  environment-provided OpenRouter credentials only.
