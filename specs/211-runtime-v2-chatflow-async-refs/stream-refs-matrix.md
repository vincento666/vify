# Runtime Stream And Ref Matrix

## Public Entrypoints

| Surface | Endpoint | Shape | Runtime path | SSE | Compatibility |
| --- | --- | --- | --- | --- | --- |
| Workflow | `POST /api/v1/workflows/{id}/runs` | run-first async | runtime v2 `startOnly`, durable job | refs only | Primary Workflow start |
| Workflow | `POST /api/v1/workflows/{id}/runs:stream` | run-first stream | runtime v2 `startOnly`, durable job | yes, durable events | Primary Workflow SSE |
| Workflow | `POST /api/v1/workflows/{id}/runs-v2` | run-first async | runtime v2 service | refs only | Migration alias |
| Workflow | `POST /api/v1/workflows/{id}/runs-legacy` | synchronous projection | legacy `WorkflowService.execute` | no | Explicit legacy compatibility |
| Chatflow | `POST /api/v1/chatflows/{id}/runs` | run-first async | runtime v2 `startOnly`, durable job | refs only | Primary Chatflow run start |
| Chatflow | `POST /api/v1/chatflows/{id}/runs:stream` | run-first stream | runtime v2 `startOnly`, durable job | yes, durable events | Primary Chatflow SSE |
| Chatflow | `POST /api/v1/chatflows/{id}/runs-v2` | run-first async | runtime v2 service | refs only | Migration alias |
| Chatflow | `POST /api/v1/chatflows/{id}/runs-legacy` | synchronous projection | legacy Chatflow execution | no | Explicit legacy compatibility |
| Chatflow | `POST /api/v1/chatflows/{id}/messages` | session/message-first | runtime v2 start + durable job + short wait | refs; callers can stream refs | Customer-chat gateway |
| RuntimeLab SOP | `POST /api/v1/runtime-lab/messages` and `/sessions/{id}/messages` | session/message-first | SOP adapter via `RuntimeInvocationGateway` | session refs in response | Product SOP gateway |
| Customer Assistant | `POST /api/v1/customer-assistant/messages` and `/sessions/{id}/messages` | session/message-first | worker refs + Chatflow runtime refs | session and worker event streams | Operator-facing gateway |

## Runtime Run Refs

All runtime-v2 starts expose the same ref family:

| Ref | Endpoint | Purpose | Recovery |
| --- | --- | --- | --- |
| `statusRef` | `GET /api/v1/runtime-runs/{runId}` | Current run status and ownership | Rebuilds the full six-ref family, including `runtimeRefs`, from runId |
| `eventsRef` | `GET /api/v1/runtime-runs/{runId}/events?afterSequence=N` | Durable event replay | Replays events after the caller's last durable sequence |
| `eventStreamRef` | `GET /api/v1/runtime-runs/{runId}/events/stream?afterSequence=N` | SSE reconnect stream with heartbeat support | Reconnects from the same durable cursor as `eventsRef` |
| `nodesRef` | `GET /api/v1/runtime-runs/{runId}/nodes` | Runtime node state for canvas/task panels | Rehydrates node-run state from durable node rows |
| `resultRef` | `GET /api/v1/runtime-runs/{runId}/result` | Terminal or current result projection | Returns the same status/result projection and full six-ref family as `statusRef` |
| resume | `POST /api/v1/runtime-runs/{runId}/resume` | Resume interrupted run from checkpoint | Uses the existing run checkpoint and returns same-run refs |
| cancel | `POST /api/v1/runtime-runs/{runId}/cancel` | Mark running/interrupted run cancelled | Uses runId idempotently and returns the updated run projection |

## Internal Invocation Modes

| Mode | Gateway call | Completes inline | Durable job | Returned data |
| --- | --- | --- | --- | --- |
| `startOnly` | `start_only` | no | caller-owned | refs, status, empty events |
| `startAndWait` | `start_and_wait` | yes | no | refs, final/current result, events |
| `startAndStreamRef` | `start_and_stream_ref` | no | optional callback | refs, `streamRef`, optional `backgroundJob` |
| `resumeAndWait` | `resume_and_wait` | yes | no | same run refs, result, events |

SOP and customer-assistant async refs mode uses `startAndStreamRef` with a
Chatflow runtime job enqueue callback. Sync compatibility mode still uses
`startAndWait`.

## 213.1 amendment — RuntimeInvocationRefs DTO

Spec 213 slice 213.1 formalised the six-ref contract behind a frozen dataclass
`RuntimeInvocationRefs` in `app/modules/workflow/domain/runtime_invocation_gateway.py`.

Fields (camelCase to match envelope keys and frontend payload):

| Field | Source path | Type |
|-------|-------------|------|
| runId | runtime-run id | int |
| statusRef | GET /api/v1/runtime-runs/{runId} | str |
| eventsRef | GET /api/v1/runtime-runs/{runId}/events | str |
| eventStreamRef | SSE /api/v1/runtime-runs/{runId}/events/stream | str |
| nodesRef | GET /api/v1/runtime-runs/{runId}/nodes | str |
| resultRef | GET /api/v1/runtime-runs/{runId}/result | str |

Helpers:
- `RuntimeInvocationRefs.from_envelope(envelope_dict)`: parse from gateway dict
- `RuntimeInvocationRefs.to_dict()`: round-trip to dict matching envelope keys

Contract test: `tests/contract/runtime_gateway/test_six_ref_dto.py` locks this DTO shape;
subsequent slices (213.2 / 213.3 / 213.4) MUST import this DTO rather than re-defining
local ref shapes.

## 213.5 amendment — runId recovery contract

Spec 213 slice 213.5 locks disconnect recovery through
`tests/contract/runtime_recovery/test_runid_recovery.py`.

Given only `runId`, callers can rebuild:

- `GET /api/v1/runtime-runs/{runId}` status plus all six refs.
- `GET /api/v1/runtime-runs/{runId}/events?afterSequence=N` durable event replay.
- `GET /api/v1/runtime-runs/{runId}/nodes` durable node state.
- `GET /api/v1/runtime-runs/{runId}/result` current or terminal result plus all six refs.
