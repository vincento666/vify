# Plan 064: Hify Runtime V2 Core Node Coverage Pack 1

## Node Order

Recommended order:

```text
HUMAN_INPUT
TEXT_PROCESS
JSON_PARSE
VARIABLE_ASSIGN
VARIABLE_AGGREGATION
CONDITION
INTENT_RECOGNITION
INFORMATION_COLLECTION
```

Keep `LLM`, tool, agent, nested workflow, and code nodes for later packs.
`INFORMATION_COLLECTION` is included only for deterministic/schema-driven
behavior. If it needs LLM extraction, retrieval, tools, or provider prompts, the
whole graph remains unsupported for v2 in this pack.

## Compatibility Strategy

For each supported node:

- build a small legacy run fixture;
- build the same v2-compatible graph;
- compare outputs and route decisions;
- compare variable scope and failure behavior;
- compare checkpoint/resume shape where relevant.

## Event Strategy

Emit:

- `workflow_node_started`;
- `workflow_node_completed`;
- `workflow_node_failed`;
- L2 events only where the node has domain meaning, such as
  `route_selected`, `variable_collected`, or `chatflow_interrupted`.
