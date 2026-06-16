# Spec 064: Hify Runtime V2 Core Node Coverage Pack 1

## Goal

Expand Hify shared runtime v2 node coverage to the first practical set of
core deterministic nodes.

This is the node-coverage MVP that makes v2 useful for real Hify Chatflow and
later Hify Workflow graphs without taking on LLM/tool/agent complexity.

## Dependency

064 depends on:

- 062 Hify Workflow/Chatflow shared runtime v2 core;
- 063 Hify Chatflow runtime v2 facade MVP.

## Product Boundary

In scope:

- `START`, `END`, `MESSAGE`, `QUESTION`, `HUMAN_INPUT`;
- `CONDITION`, `INTENT_RECOGNITION`;
- `VARIABLE_ASSIGN`, `VARIABLE_AGGREGATION`;
- deterministic/schema-driven `INFORMATION_COLLECTION`;
- `TEXT_PROCESS`, `JSON_PARSE`;
- graph-level compatibility checks for these nodes;
- shared runtime L1/L2 events for supported nodes.

Out of scope:

- `LLM`, `KNOWLEDGE`, `TOOL_CALL`, `API_CALL`, `AGENT_CALL`;
- `EXECUTE_WORKFLOW`, `TRANSFER_TO_HUMAN`, `CODE`;
- node-level v1/v2 mixed execution;
- full Hify Workflow facade rollout.

## Hard Constraints

- Coverage must be implemented in the shared runtime core, not only Chatflow.
- Unsupported nodes must keep the whole graph out of v2.
- Node outputs must match legacy engine semantics for supported nodes.
- Route decisions, variable scopes, checkpoint behavior, and failure behavior
  must match legacy semantics for supported nodes.
- `INFORMATION_COLLECTION` is supported only when it can run without hidden
  LLM/retrieval/tool behavior.
- Node event payloads must be redacted and should not leak raw credentials or
  internal provider payloads.
- Existing sync Workflow/Chatflow tests must remain green.

## Information Collection Boundary

If the existing `INFORMATION_COLLECTION` behavior depends on LLM extraction,
knowledge retrieval, tool calls, or provider-specific prompts, that graph is not
covered by 064 and must be reported as unsupported for v2.

064 may support only the deterministic subset, such as schema validation,
missing-field detection from already structured input, and checkpoint emission.

## Acceptance Criteria

- Supported node set is explicit and tested.
- Node output compatibility is proven against legacy behavior.
- Deterministic `INFORMATION_COLLECTION` support is separated from any
  LLM-dependent behavior.
- Runtime events are emitted for supported nodes.
- Unsupported node reports are clear and include node key/type.
- Chatflow v2 facade can use the expanded coverage.

## MVP Exit

064 is complete when deterministic core nodes can run through shared runtime v2
without mixing v1/v2 execution inside a run.
