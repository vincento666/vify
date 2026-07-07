# Runtime DAG Semantics

Spec 214 defines the shared DAG vocabulary used by Workflow, Chatflow, SOP, and
later runtime v2 scheduler work. This document is the semantic source for
`app.modules.runtime.api.schemas`.

## Edge Semantics

An edge connects one source node port to one target node port. `sourceNodeKey`,
`sourcePortKey`, `targetNodeKey`, and `targetPortKey` identify the connection.
`sourcePortKey` defaults to `default`; `targetPortKey` defaults to `input`.

One source port may connect to multiple target nodes only when the matching
`PortSpec.allowFanOut` is true or when the port belongs to an explicit branch
group that selects all targets under that port.

## Port Semantics

Ports are typed as:

- `default`: ordinary continuation from a node.
- `branch`: conditional, intent, or router branch output.
- `error`: failure or exception branch output.

Fan-out from a default port is explicit, never accidental. Canvas validation in
slice 214.2 must reject ambiguous multi-target default ports unless
`allowFanOut` is true.

## Branch Group Semantics

A branch group is the set of branch ports owned by a branching node. The group
records the selected and skipped port keys for one run. `selectionMode=single`
means one port is selected; `selectionMode=multi` means multiple ports may be
selected.

When a port is selected, all targets connected to that selected port enter the
runnable frontier. Ports not selected are skipped, and downstream nodes that
depend only on skipped upstreams become skipped.

## Skipped State Semantics

`NodeSelectionState.state` uses these values:

- `pending`: node has not been selected or skipped yet.
- `selected`: node is part of the active run graph.
- `skipped`: node is not part of the active run graph.
- `running`: selected node is executing.
- `waiting`: selected node interrupted and awaits input or resume.
- `completed`: selected node finished successfully.
- `failed`: selected node failed.
- `cancelled`: selected node was cancelled.

Skipped upstreams do not block an implicit join. A join-like node waits only for
selected upstreams that are required for its target port.

## Node Selection State Lifecycle

Runtime v2 records `selection_state` on each `workflow_node_run`. Existing
single-path execution remains unchanged in spec 214: the runtime still advances
with the legacy next-node rule, while the DAG selection builder projects the
future frontier state for scheduler work in spec 215.

Lifecycle rules:

1. `pending`: a node is known but not yet selected, skipped, running, or
   terminal.
2. `selected`: a selected source port reaches the node.
3. `skipped`: every known upstream path to the node is skipped.
4. `running`: an executed selected node has an active node-run row.
5. `waiting`: an executed selected node interrupted for input or resume.
6. `completed`, `failed`, or `cancelled`: terminal execution state for an
   executed selected node.

For implicit joins, `selectedUpstreamNodeKeys` and `skippedUpstreamNodeKeys`
record which upstreams matter for the current run. A skipped upstream is
evidence, not a blocker; the join waits only for selected upstreams.

## Frontier Algorithm

The scheduler frontier is derived from the node selection graph and the current
execution state. A node enters `runnableNodeKeys` when it is selected, is not
already running/waiting/terminal, and every selected upstream node is
`completed`.

Nodes that are selected but still depend on incomplete selected upstreams stay
in `waitingNodeKeys`. Explicit runtime `waiting` nodes also stay out of the
runnable frontier until they are resumed. Nodes reached only through skipped
ports enter `skippedNodeKeys` and never block an implicit join.

The frontier order is deterministic: nodes keep their canvas definition order.
This lets later concurrent execution fan out from a stable frontier while event
sequence and node-run writes can still be serialized by the runtime layer.

For explicit START fan-out, START remains a virtual input node. When its
`default` port is marked `allowFanOut`, runtime records the virtual default port
as selected before the first frontier calculation, so all selected downstream
targets enter the same wave. For LLM, Knowledge, and Agent waves, runtime
creates all node-run rows and emits all `RUNNING` events before completing any
node in that wave. This makes DAG concurrency observable while preserving
serialized event sequence allocation.

## Terminal Semantics

A selected node with no selected downstream is a terminal leaf. Terminal
side-effect nodes are legal when their edge or node evidence marks the path as a
side-effect terminal. Runtime must not fail such paths with "next node not
found".

## Final Output Rules

Chatflow final output prioritizes visible user-facing results:

1. End node output. When an executed End node has visible output, runtime keeps
   that exact output payload as the terminal run output for backward
   compatibility.
2. Answer mapping. If End is present but has no visible value, runtime may pick
   the closest non-End node output that explicitly maps `answer`.
3. Priority reply node. Reply candidates with `replyPriority`,
   `reply_priority`, `priorityReply`, or `priority_reply` are ordered by the
   numeric priority value; the highest candidate becomes the visible reply.
4. Explicit no-reply summary when all selected paths only produce side effects.
   The summary is structured and must not be converted into an assistant
   message.

Chatflow requires at least one selected path to produce a visible reply, wait
for input, transfer to human, or return an explicit no-reply result.

### Chatflow final reply selection

In multi-path Chatflow runs, side-effect-only node outputs are excluded from
answer mapping and priority reply candidates, even if they carry fields such as
`answer` for internal delivery evidence. They only contribute to
`sideEffectEvidence`. This keeps notification, write, and handoff side effects
from becoming user-visible assistant replies when another selected branch
produces the actual answer.

Workflow may be side-effect-only. In that case it still returns run status,
node events, and side-effect evidence through runtime refs.

The side-effect-only summary shape is:

```json
{
  "sideEffectOnly": true,
  "summary": "side_effect_only_completed",
  "sideEffectEvidence": [
    {
      "nodeKey": "notify",
      "nodeType": "CODE",
      "status": "SUCCEEDED",
      "output": {}
    }
  ]
}
```

Chatflow adds `"noReply": true` to the same shape. Runtime response helpers must
return `answer: null` and must not emit `assistant_message` for that payload.

## Failure Strategy Matrix

Runtime v2 supports four scheduler-level failure strategies for nodes that may
raise recoverable execution errors: `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`,
`EXECUTE_WORKFLOW`, and `AGENT_CALL`.

| Strategy | `errorBehavior` | Runtime effect | Downstream route |
| --- | --- | --- | --- |
| fail-fast | `fail` | Node run becomes `FAILED`; the runtime run fails immediately. | none |
| continue-on-error | `continue` | Node run is recorded as completed with `success=false`, `error`, and failure evidence. | default outlet |
| error branch | `branch` | Node run is recorded as completed with `success=false`, `route=error`, and failure evidence. | `error` outlet |
| partial success | `partial` | Node run is recorded as completed with `success=false`, `partialSuccess=true`, and `failureStrategy=partial_success` evidence. | default outlet |

Only `branch` requires an explicit error edge. `continue` and `partial` keep the
active path moving through the default outlet, while preserving failure evidence
for final output rendering, debug panels, and downstream templates.

## Event Sequence Guarantee

Runtime v2 event rows are ordered by `(run_id, sequence)`. Within one backend
process, sequence allocation for a single run is guarded by a per-run lock so
frontier nodes that complete at the same time still append strictly monotonic
event sequences.

The database unique index on `(run_id, sequence)` remains the hard consistency
guard. If a sequence conflict is detected, the append path rolls back, reads
the latest sequence again, and retries before surfacing an error. Event listing
APIs return rows sorted by ascending `sequence` and `id`.

This guarantee covers in-process frontier concurrency. Cross-process worker
lease, heartbeat, retry, and backpressure semantics are owned by the later
worker/runtime specs and must not be inferred from this scheduler slice.
