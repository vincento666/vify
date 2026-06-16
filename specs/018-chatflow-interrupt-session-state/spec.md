# Spec 018: Chatflow Interrupt And Session State

## Goal

Make Chatflow runtime stateful enough for commercial customer service: a flow can pause for user input, resume from the same execution point, preserve scoped variables and bounded conversation history, and expose reliable event records for debugging and later observation.

## Product Boundary

- Starts after 015 interactive Chatflow nodes exist and before 019 channel/handoff work.
- Supports single-flow interrupt/resume. It does not implement Dify-style cross-flow Task Stack or automatic dynamic task switching.
- Uses the shared FlowGraph schema and `flow_type=CHATFLOW`.
- Extends the existing Chatflow run/profile behavior instead of creating a separate engine.
- Provides durable-enough local persistence first. Redis can be added later behind the same checkpoint store interface.
- Does not support nested Chatflow interrupts from subworkflow calls unless explicitly enabled by a later spec.

## Commercial Customer Service Value

A customer service Chatflow must remember the current conversation, collected fields, pending question, user identity, channel, and incomplete work. Without interrupt/resume and scoped variables, QUESTION, HUMAN_INPUT, INFORMATION_COLLECTION, and later handoff cannot be reliable.

## State Model

### Session

`ChatflowSession` tracks:

- `session_id`
- `chatflow_id`
- `conversation_id`
- `user_id`
- `channel`
- `channel_id`
- `status`: active, waiting, completed, failed, expired
- `current_run_id`
- `created_at`, `updated_at`, `expires_at`

### Run

`ChatflowRun` tracks:

- `run_id`
- `session_id`
- `chatflow_id`
- `status`
- `input`
- `output`
- `events`
- `node_runs`
- `checkpoint_id` when waiting

### Event

Events are append-only:

- `message`: content emitted by MESSAGE or follow-up output.
- `interrupt`: flow is waiting for user/manual data.
- `resume`: user/manual data resumes the run.
- `tool_call`: resource invocation evidence from 017 when present.
- `node_started`
- `node_completed`
- `done`
- `error`

### Checkpoint

Checkpoint stores:

- `checkpoint_id`
- `run_id`
- `event_id`
- `pending_node_key`
- `next_edge_hint`
- `execution_context`
- `node_outputs`
- `variable_scopes`
- `resume_schema`
- `expires_at`

## Variable Scopes

Chatflow variable resolution order:

1. external input for current request.
2. system variables.
3. conversation variables.
4. user variables.
5. channel variables.
6. global/application variables.
7. upstream node outputs.

System variables include:

- `sys.query`
- `sys.conversation_id`
- `sys.user_id`
- `sys.channel`
- `sys.channel_id`
- `sys.message_id`
- `sys.round`
- `sys.now`
- `sys.files`

Conversation variables default to 24-hour inactivity expiration. Checkpoints default to 7-day expiration unless configured otherwise.

## Resume Contract

Resume requires:

- `run_id`
- `event_id`
- `resume_data`
- optional idempotency key.

Resume behavior:

- Validate pending checkpoint exists and is waiting.
- Validate resume data against the interrupt node schema.
- Merge resume data into execution context and scoped variables.
- Continue from the checkpoint, not from START.
- Reject duplicate resume with the same idempotency key unless it is a safe replay.
- Reject resume when session expired, checkpoint expired, or event belongs to another run.

## Node Behavior

- QUESTION emits `interrupt` with answer schema and waits.
- HUMAN_INPUT emits `interrupt` with manual input or approval schema and waits.
- INFORMATION_COLLECTION emits `message` plus `interrupt` while required fields are missing, then continues when complete.
- MESSAGE emits `message` and continues without checkpoint.
- LLM/INTENT_RECOGNITION/INFORMATION_COLLECTION may read bounded conversation history when enabled.

## API Surface

MVP endpoints:

- `POST /api/v1/chatflows/{chatflow_id}/runs`
  - starts or continues a session according to input profile.
- `POST /api/v1/chatflows/{chatflow_id}/runs/{run_id}/resume`
  - resumes a pending interrupt.
- `GET /api/v1/chatflows/{chatflow_id}/sessions/{session_id}`
  - returns session state, variables, and current waiting event.
- `GET /api/v1/chatflows/{chatflow_id}/runs/{run_id}/events`
  - returns ordered events for debug and observe surfaces.

Existing run endpoints may be reused when they preserve this contract.

## Frontend Behavior

- Chatflow test panel can start a session, answer a pending question, and continue from the same run.
- Node-test drawer can simulate resume for a selected interrupt-capable node.
- Bottom debug dock shows event timeline, checkpoint status, scoped variables, and current pending node.
- Variable panels show conversation/user/channel values that changed during the test run.
- Expired or duplicate resume errors are visible and actionable.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 018.1 Session, event, and checkpoint model | Chatflow run can store session/event/checkpoint records | RED: model/repository tests fail; Unit: serializers; Integration: create waiting session |
| 018.2 Resume API | QUESTION/HUMAN_INPUT/INFO_COLLECTION resume from checkpoint | RED: resume tests fail; Unit: checkpoint merge; Integration: resume same run; E2E: ask then answer |
| 018.3 Scoped variables and history | Conversation/user/channel/global/system variables resolve and persist correctly | RED: variable scope tests fail; Unit: resolver; Integration: variable assignment then resume; E2E: picker/debug values visible |
| 018.4 Runtime event timeline UI | Chatflow debug panel shows event timeline, waiting state, and resume result | RED: frontend state tests fail; E2E: event timeline; Browser UAT screenshots |
| 018.5 Reliability guards | Idempotency, expiration, wrong event, duplicate resume, and failed resume are safe | RED: reliability tests fail; Integration: guard cases; E2E: visible errors |

## Evidence

- 015 defines MESSAGE, QUESTION, HUMAN_INPUT, and INFORMATION_COLLECTION as separate runtime behaviors.
- 012 defines Chatflow system variables, scoped variable panels, and conversation-shaped run/profile UI.
- HiAgent/Dify research in conversation context establishes the need for single-flow interrupt/resume before cross-flow task stack work.
