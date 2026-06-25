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

| Ref | Endpoint | Purpose |
| --- | --- | --- |
| `statusRef` | `GET /api/v1/runtime-runs/{runId}` | Current run status and ownership |
| `eventsRef` | `GET /api/v1/runtime-runs/{runId}/events?afterSequence=N` | Durable event replay |
| `eventStreamRef` | `GET /api/v1/runtime-runs/{runId}/events/stream?afterSequence=N` | SSE reconnect stream with heartbeat support |
| `nodesRef` | `GET /api/v1/runtime-runs/{runId}/nodes` | Runtime node state for canvas/task panels |
| `resultRef` | `GET /api/v1/runtime-runs/{runId}/result` | Terminal or current result projection |
| resume | `POST /api/v1/runtime-runs/{runId}/resume` | Resume interrupted run from checkpoint |
| cancel | `POST /api/v1/runtime-runs/{runId}/cancel` | Mark running/interrupted run cancelled |

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
