# Node Field Audit Baseline

This baseline records the current state before Spec 194 implementation slices are integrated.

## Node Catalog

Source of truth: `frontend/src/views/workflow/flowGraph.ts` and `frontend/src/views/workflow/nodeConfig.ts`.

The current catalog has 20 node types:

`START`, `LLM`, `CONDITION`, `KNOWLEDGE`, `API_CALL`, `TOOL_CALL`, `EXECUTE_WORKFLOW`, `AGENT_CALL`, `TRANSFER_TO_HUMAN`, `CODE`, `TEXT_PROCESS`, `JSON_PARSE`, `VARIABLE_AGGREGATION`, `VARIABLE_ASSIGN`, `INTENT_RECOGNITION`, `MESSAGE`, `QUESTION`, `HUMAN_INPUT`, `INFORMATION_COLLECTION`, `END`.

## Current Runtime Coverage

Legacy engine dispatches all 20 node types.

Runtime v2 currently supports 18 node types in `_SUPPORTED_CORE_NODE_TYPES`; `API_CALL` and `TOOL_CALL` are still missing from the v2 whitelist and dispatch. This blocks phase 1 completion.

Existing focused backend checks before Spec 194 worker integration:

```text
rtk uv run pytest -q tests/unit/workflow/test_runtime_v2_core.py tests/unit/workflow/test_publish_validation.py tests/unit/workflow/test_runtime_parity.py tests/integration/workflow/test_resource_policy.py
15 passed, 1 warning
```

This proves the current endpoint/publish validation and legacy resource policy tests pass. It does not prove runtime v2 API/Tool productionization.

## Field Risk Summary

| Node | Baseline status | Phase 1 gap |
| --- | --- | --- |
| START | Start variables UI exists; built-in names recognized | Need run/publish validation for required/type/default and system variable write protection |
| LLM | Model/prompt/skills/tool settings/params UI exists; node model config can drive runtime v2 | v2 callable tools need tool runtime injection and evidence; error routing needs `continue`/`branch` |
| CONDITION | Branch row UI and endpoint validation exist | Error/fallback endpoint semantics must stay aligned with backend validation |
| KNOWLEDGE | Resource selector, query, mode, topK, score, rerank exist | Resource readiness validation must be part of publish/run checks |
| API_CALL | Resource selector, input mapping, endpoint, method, headers, body, timeout, output exist | Missing complete governance fields: auth/query params/status policy/retry/backoff/error route/schema preview in ordinary path; v2 executor missing |
| TOOL_CALL | Resource selector, schema mappings, retry, error behavior, output exist | Missing ordinary timeout/allowWrite/permission-boundary visibility; v2 executor missing |
| EXECUTE_WORKFLOW | Resource selector, mappings, timeout/maxDepth defaults exist | Nested call must use immutable published snapshot and support error policy |
| AGENT_CALL | Agent selector, message template, mappings, history, stream, outputs exist | Resolver must bind to snapshot and support error policy |
| TRANSFER_TO_HUMAN | Queue/reason/priority/SLA UI and runtime evidence exist | No phase 1 production blocker beyond validation/evidence |
| CODE | Language/code/timeout/output UI exists; v2 executor exists | Error policy must support `continue`/`branch` |
| TEXT_PROCESS | Operation/template/source/pattern/replacement/output exist | No phase 1 production blocker beyond validation/evidence |
| JSON_PARSE | Source and mapping rows exist | Variable/type validation should block illegal refs |
| VARIABLE_AGGREGATION | Strategy/groups/output exist | Type/default/null policy evidence is partial; phase 1 needs baseline validation |
| VARIABLE_ASSIGN | Scope/target/source UI exists | Must block writes to system variables and expose scoped variable evidence |
| INTENT_RECOGNITION | Input/classifier/history/intents/output exist | Endpoint validation already started; model readiness and branch evidence need closure |
| MESSAGE | Content/stream target/fallback/output exist | Runtime/debug evidence for fallback fields needs closure |
| QUESTION | Question/type/resume/timeout/options/output exist | Runtime v2 waiting/resume evidence is in progress; timeout policy needs validation |
| HUMAN_INPUT | Prompt/approval/assignee/schema/output exist | Runtime v2 checkpoint/evidence exists; schema validation needs closure |
| INFORMATION_COLLECTION | Input/key/history/write/extractor/maxRounds/stream/fields/output exist | LLM-dependent mode must be blocked or provider-backed; variable scope writes need evidence |
| END | Output/answer content exist | Final response/stream fields must be tied to runtime/debug evidence |

## Blocking Phase 1 Items

- Add runtime v2 `API_CALL` and `TOOL_CALL` support or precise production-safety rejection.
- Inject MCP/API tool runtime into runtime v2 LLM executable path.
- Extend unified error routing and endpoint validation for named failure nodes.
- Bind all runtime v2 resolver setup to immutable run snapshots, including nested workflow calls.
- Close API/Tool governance field gaps and prove sanitized evidence.
- Produce final node-by-node evidence report after implementation and gates.
