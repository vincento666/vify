# Runtime V2 Node Compatibility Matrix

Source spec: `specs/217-runtime-v2-node-compatibility-matrix/`

Runtime V2 executes first-class canvas nodes through the frontier scheduler. The
registry source of truth is `app/modules/runtime/api/node_registry.py`; this
document mirrors the public compatibility contract for reviewers and UAT.

This document separates two concepts:

- implementation compatibility: an executor or documented runtime path exists;
- evidence status: Workflow and Chatflow UAT have actually proven the node under
  the relevant async/runtime semantics.

Spec 223 owns the evidence-status closure. Rows marked `partial`,
`automated-only`, or `missing` must not be used as proof that the full
Workflow/Chatflow product behavior is complete.

## Compatibility Summary

| Node type | Executor mapping | Status | Node run | Runtime event | DAG isolation | Chatflow | Workflow |
|---|---|---|---|---|---|---|---|
| START | RuntimeV2 input context virtual executor | virtual | virtual | run_event | yes | yes | yes |
| MESSAGE | MessageNodeExecutor / inline RuntimeV2 message path | reused | durable | node_event | yes | yes | yes |
| QUESTION | QuestionNodeExecutor / RuntimeV2 checkpoint path | native | durable | node_event | yes | yes | yes |
| HUMAN_INPUT | HumanInputNodeExecutor | reused | durable | node_event | yes | yes | yes |
| LLM | LlmNodeExecutor | reused | durable | node_event | yes | yes | yes |
| KNOWLEDGE | KnowledgeNodeExecutor | reused | durable | node_event | yes | yes | yes |
| AGENT_CALL | AgentCallNodeExecutor | reused | durable | node_event | yes | yes | yes |
| API_CALL | ApiCallNodeExecutor | reused | durable | node_event | yes | yes | yes |
| TOOL_CALL | ToolCallNodeExecutor | reused | durable | node_event | yes | yes | yes |
| EXECUTE_WORKFLOW | ExecuteWorkflowNodeExecutor | reused | durable | node_event | yes | yes | yes |
| CODE | CodeNodeExecutor | reused | durable | node_event | yes | yes | yes |
| TEXT_PROCESS | TextProcessNodeExecutor | reused | durable | node_event | yes | yes | yes |
| JSON_PARSE | JsonParseNodeExecutor | reused | durable | node_event | yes | yes | yes |
| VARIABLE_ASSIGN | VariableAssignNodeExecutor | reused | durable | node_event | yes | yes | yes |
| VARIABLE_AGGREGATION | VariableAggregationNodeExecutor | reused | durable | node_event | yes | yes | yes |
| CONDITION | ConditionNodeExecutor | reused | durable | node_event | yes | yes | yes |
| INTENT_RECOGNITION | IntentRecognitionNodeExecutor | reused | durable | node_event | yes | yes | yes |
| INFORMATION_COLLECTION | InformationCollectionNodeExecutor | reused | durable | node_event | yes | yes | yes |
| TRANSFER_TO_HUMAN | RuntimeV2 checkpointed transfer path / TransferToHumanNodeExecutor | native | durable | node_event | yes | yes | product-difference: Chatflow only |
| END | EndNodeExecutor | reused | durable | node_event | yes | yes | yes |

## Evidence Status

Status values:

- `covered`: latest closure evidence proves the product behavior.
- `partial`: some runtime/browser evidence exists, but not the full closure
  matrix.
- `automated-only`: tests exist, but latest browser/product UAT evidence is not
  complete.
- `not-applicable`: product boundary excludes this node for that flow.
- `missing`: no sufficient closure evidence is recorded.

| Node type | Workflow evidence | Chatflow evidence | Closure owner |
|---|---|---|---|
| START | partial | partial | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| MESSAGE | partial | partial | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| QUESTION | automated-only | partial | [223.5](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| HUMAN_INPUT | automated-only | missing | [223.5](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| LLM | partial | partial | [223.2/223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| KNOWLEDGE | automated-only | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| AGENT_CALL | automated-only | automated-only | [223.2/223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| API_CALL | partial | automated-only | [223.2/223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| TOOL_CALL | automated-only | automated-only | [223.2/223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| EXECUTE_WORKFLOW | automated-only | automated-only | [223.2/223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| CODE | partial | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| TEXT_PROCESS | automated-only | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| JSON_PARSE | automated-only | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| VARIABLE_ASSIGN | automated-only | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| VARIABLE_AGGREGATION | automated-only | automated-only | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| CONDITION | partial | partial | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| INTENT_RECOGNITION | automated-only | partial | [223.5](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| INFORMATION_COLLECTION | automated-only | partial | [223.5](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| TRANSFER_TO_HUMAN | not-applicable | partial | [223.5](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |
| END | partial | partial | [223.3](../../specs/223-runtime-v2-boundary-parallel-visual-closure/tasks.md) |

## Chatflow / Workflow Parity

The registry publishes capability schemas for each flow type. Rows must stay
identical unless a product semantic difference is explicit.

| Node type | Chatflow capability schema | Workflow capability schema | Parity |
|---|---|---|---|
| START | `run.start`, `input.context` | `run.start`, `input.context` | same |
| MESSAGE | `message.output`, `side_effect.idempotency` | `message.output`, `side_effect.idempotency` | same |
| QUESTION | `checkpoint.wait`, `checkpoint.resume` | `checkpoint.wait`, `checkpoint.resume` | same |
| HUMAN_INPUT | `checkpoint.wait`, `checkpoint.resume` | `checkpoint.wait`, `checkpoint.resume` | same |
| LLM | `model.call`, `node_run.evidence` | `model.call`, `node_run.evidence` | same |
| KNOWLEDGE | `knowledge.search`, `node_run.evidence` | `knowledge.search`, `node_run.evidence` | same |
| AGENT_CALL | `agent.call`, `recursion_guard`, `node_run.evidence` | `agent.call`, `recursion_guard`, `node_run.evidence` | same |
| API_CALL | `api_resource.call`, `side_effect.idempotency` | `api_resource.call`, `side_effect.idempotency` | same |
| TOOL_CALL | `tool_resource.call`, `side_effect.idempotency`, `resource_policy.allow_write` | `tool_resource.call`, `side_effect.idempotency`, `resource_policy.allow_write` | same |
| EXECUTE_WORKFLOW | `subworkflow.run`, `side_effect.idempotency`, `recursion_guard` | `subworkflow.run`, `side_effect.idempotency`, `recursion_guard` | same |
| CODE | `sandbox.compute`, `node_run.evidence` | `sandbox.compute`, `node_run.evidence` | same |
| TEXT_PROCESS | `text.transform`, `node_run.evidence` | `text.transform`, `node_run.evidence` | same |
| JSON_PARSE | `json.parse`, `node_run.evidence` | `json.parse`, `node_run.evidence` | same |
| VARIABLE_ASSIGN | `runtime_variable.write`, `side_effect.execution_record` | `runtime_variable.write`, `side_effect.execution_record` | same |
| VARIABLE_AGGREGATION | `runtime_variable.aggregate`, `selected_upstream.outputs` | `runtime_variable.aggregate`, `selected_upstream.outputs` | same |
| CONDITION | `branch.select`, `port.default`, `selection_state` | `branch.select`, `port.default`, `selection_state` | same |
| INTENT_RECOGNITION | `intent.route`, `branch.select`, `selection_state` | `intent.route`, `branch.select`, `selection_state` | same |
| INFORMATION_COLLECTION | `checkpoint.wait`, `checkpoint.resume`, `conversation_variable.write` | `checkpoint.wait`, `checkpoint.resume`, `conversation_variable.write` | same |
| TRANSFER_TO_HUMAN | `handoff.proposed_action`, `checkpoint.wait`, `side_effect.idempotency` | `product_difference.not_available` | Chatflow-only handoff request; Workflow intentionally has no conversation handoff target. |
| END | `final_output.resolve`, `node_run.evidence` | `final_output.resolve`, `node_run.evidence` | same |

## Side-Effect And Protection Matrix

| Node type | Side effect | Current Runtime V2 protection |
|---|---|---|
| START | none | Run-level idempotency key records `workflow_run_started`. |
| MESSAGE | message output | `sideEffectProtection` idempotency key plus durable node-run output and message events. |
| QUESTION | waiting checkpoint | Checkpoint/event link plus resume idempotency key. |
| HUMAN_INPUT | waiting checkpoint | Checkpoint/event link plus resume idempotency key. |
| LLM | model call | Durable node-run evidence; provider retry semantics stay outside spec 217. |
| KNOWLEDGE | knowledge search | Read-only facade call plus durable node-run evidence. |
| AGENT_CALL | agent invocation | Timeout, recursion guard, and durable node-run evidence. |
| API_CALL | external API call | `sideEffectProtection` idempotency key is copied into API Resource evidence; raw URL mode is rejected by compatibility check. |
| TOOL_CALL | MCP/API tool call | `sideEffectProtection` idempotency key plus resource policy, `allowWrite`, retry evidence, and sanitized input. |
| EXECUTE_WORKFLOW | nested workflow run | `sideEffectProtection` idempotency key plus nested run evidence and recursive target guard. |
| CODE | sandboxed compute | Restricted sandbox and durable node-run evidence. |
| TEXT_PROCESS | none | Pure transform. |
| JSON_PARSE | none | Pure transform. |
| VARIABLE_ASSIGN | runtime variable write | `sideEffectProtection` execution record plus ExecutionContext branch clone and durable node-run evidence. |
| VARIABLE_AGGREGATION | none | Pure transform from selected upstream outputs. |
| CONDITION | branch selection | Selected port evidence in downstream selection state. |
| INTENT_RECOGNITION | optional model call and branch selection | Selected port evidence in downstream selection state. |
| INFORMATION_COLLECTION | waiting checkpoint and optional conversation variable write | Checkpoint/event link plus resume idempotency key. |
| TRANSFER_TO_HUMAN | handoff request | `sideEffectProtection` proposed action, runtime-v2 handoff id, and checkpointed waiting event. |
| END | run final output | Final-output resolver and durable node-run evidence. |

## Notes

- START is deliberately virtual in Runtime V2. The scheduler seeds `start` in
  context and records run-level start events instead of creating a durable
  node-run row.
- The frontier scheduler clones context for concurrent wave branches, then
  merges branch outputs after the wave completes. That is the compatibility
  basis for the DAG isolation column.
- Compatibility checks reject raw `API_CALL` URL mode and unsupported `TOOL_CALL`
  resource modes before scheduling. Spec 217.5 tightens user-facing errors for
  invalid configurations.
- Side-effect-capable runtime v2 outputs include a stable `sideEffectProtection`
  object with `effectType`, `strategy`, `idempotencyKey`, and an execution
  record (`runId`, `nodeRunId`, `nodeKey`, `nodeType`). `TRANSFER_TO_HUMAN`
  additionally exposes a pending `proposedAction` on the interrupt payload.
- Chatflow-only transfer-to-human behavior is an explicit product difference,
  not a missing Workflow executor.
