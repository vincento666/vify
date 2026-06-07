# Plan 029: Isolated Runtime Router Lab

## Architecture

Create a new isolated runtime/router module that is DB-backed and drives only
mock SOP adapters.

The module owns:

- runtime sessions;
- runtime tasks;
- checkpoints;
- event timeline;
- idempotent message commands;
- mock SOP manifests;
- route decisions;
- temporary `runtime-lab` API schemas and router.

Existing Workflow, Chatflow, Agent, Knowledge, and handoff modules are not
called or modified by 029.

## Module Boundary

Suggested backend package:

```text
app/modules/runtime_lab/
  domain/
  infra/
  web/
```

This package may depend on shared core infrastructure such as database sessions,
time helpers, error envelopes, and FastAPI routing. No existing product module
may depend on `runtime_lab` in 029.

## Data Notes

Add schema tables for the isolated lab:

- `runtime_lab_session`
- `runtime_lab_task`
- `runtime_lab_checkpoint`
- `runtime_lab_event`
- `runtime_lab_command`

Use the `runtime_lab_` prefix to avoid implying this is already the final
unified runtime schema. Later architecture integration can migrate or rename
after the contract stabilizes.

Persistence requirements:

- one active task per session;
- monotonically increasing event sequence per session;
- idempotent message replay by `(session_id, idempotency_key)`;
- checkpoint and task state updates committed with route events;
- no raw secrets or external credentials in events.

## Routing Notes

029 uses a deliberately simple route ladder:

```text
Hard rules
  -> ResumeOffer parser
  -> strong mock SOP keyword match
  -> active task default continue
  -> reject/no match
```

There is no semantic recall or LLM/NLP classifier in 029.

Strong keyword behavior:

- If no active task exists, strong SOP trigger starts the target SOP.
- If an active task exists at an interruptible step, a different strong SOP
  trigger suspends the active task and starts the target SOP.
- If an active task exists at a non-interruptible step, the switch is rejected.

Resume behavior:

- automatic resume offer after task completion when suspended tasks exist;
- minimal text resolution for `continue`, `继续`, `继续刚才`, and `继续第一个`;
- one suspended task allowed by policy.

## Mock SOP Notes

Mock SOP manifests live in code fixtures for 029.

Required SOPs:

- `refund_ticket`;
- `change_flight`;
- `invoice_apply`.

Required step flow:

```text
collect_order_no -> confirm -> completed
```

`collect_order_no` accepts ordinary text as `order_no`. `confirm` completes only
when user input is `confirm` or `确认`.

## API Notes

Add temporary API endpoints:

```text
POST /api/v1/runtime-lab/sessions
POST /api/v1/runtime-lab/sessions/{session_id}/messages
GET  /api/v1/runtime-lab/sessions/{session_id}/tasks
GET  /api/v1/runtime-lab/sessions/{session_id}/events
```

Responses include debug evidence:

- route decision;
- active task;
- suspended tasks;
- resume offer;
- recent events.

The API keeps the existing `/api/v1` envelope convention.

## Testing Notes

029 must be built slice by slice with RED evidence first.

Test levels:

- unit:
  - mock SOP adapter;
  - keyword route decision;
  - resume-offer parser;
  - route response formatting.
- integration:
  - repository state transitions;
  - idempotency;
  - event sequence;
  - active/suspended task invariants.
- contract:
  - create session;
  - post message;
  - list tasks;
  - list events.
- API E2E:
  - start SOP;
  - continue SOP to confirm;
  - reject switch at non-interruptible step;
  - suspend/start at interruptible step;
  - complete second SOP;
  - offer and resume first SOP.

No frontend tests are required because 029 does not touch frontend files.

## Slice Order

029.1 -> 029.2 -> 029.3 -> 029.4 -> 029.5 -> 029.6 -> 029.7 -> 029.8

## 029.8 Kernel Hardening Notes

The post-029.7 API is enough for lab happy-path validation, but future
integration specs need a reusable runtime kernel boundary that does not depend
on FastAPI routing code.

029.8 moves command-level concerns into the runtime service:

- session existence validation before side effects;
- idempotent message replay by `(session_id, idempotency_key)`;
- request-hash mismatch rejection for reused idempotency keys;
- shared domain payload formatting for API responses and replay storage;
- invariant tests proving duplicate command replay does not mutate tasks or
  events.

## Git Notes

Commit after:

- initial spec/plan/tasks creation;
- each completed implementation slice after gates pass.

Do not mix unrelated repository changes into these commits.
