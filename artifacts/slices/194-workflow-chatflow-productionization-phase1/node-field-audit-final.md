# Node Field Audit Final

Scope: Spec `194-workflow-chatflow-productionization-phase1`.

Result: the current 20 text workflow/chatflow node types have at least one production-grade effect path for their configured fields: UI save/config persistence, runtime v2 execution, debug event/evidence projection, or publish/runtime validation.

Primary evidence:

- Backend wide gate: `194.6/main-backend-workflow-wide.txt` (`228 passed`, `12 subtests`).
- Runtime/API/Tool/version gate: `combined-runtime-v2-production-gate.txt`.
- Frontend full unit/rem gate: `main-frontend-unit-full.txt`, `main-frontend-focused-rem.txt`.
- SOP compatibility gate: `194.6/runtime-lab-sop-compat-gate.txt`.
- Browser UAT: `194.6/uat.md`, `194.6/runtime-v2-phase1-production-uat.json`, screenshots under `194.6/screenshots/`.
- Slice reports: `slice-reports.md`.

## Node Evidence Matrix

| Node type | Field/config effect | Runtime/debug/validation evidence |
| --- | --- | --- |
| `START` | Start variables and system input are persisted in graph config and loaded into runtime context. | Runtime v2 start/input refs covered by `test_runtime_v2_core.py`, `test_chatflow_runtime_v2_spike.py`, `test_runtime_v2_long_run_lifecycle.py`; frontend variable normalization covered by full unit gate. |
| `LLM` | `modelConfigId`, prompt, output variable, tool settings, and generation options affect provider-backed runtime or publish validation. | `test_runtime_v2_provider_backed_llm.py`, `test_runtime_v2_llm_callable_tools.py`, `test_publish_validation.py`; debug evidence redaction/fallback projection covered by frontend `workflowRunDebug`/`chatflowDebugTimeline` tests. |
| `CONDITION` | Branch rows/default branch determine endpoint validation and runtime branch selection. | `test_publish_validation.py`, `test_runtime_v2_core.py`, `test_runtime_v2_safe_node_coverage_pack2.py`; UAT validates branch selection/debug path. |
| `KNOWLEDGE` | KB/resource/query/retrieval settings drive runtime search or publish-time readiness. | `test_chatflow_runtime_v2_facade.py`, `test_workflow_runtime_v2_facade.py`, wide backend gate. |
| `API_CALL` | Resource binding, input mappings, auth mode, timeout, retry, error behavior, output schema, and sensitive headers are saved; resource identity is required by runtime/publish validation. | `test_runtime_v2_api_call_node.py`, `test_publish_validation.py`, `workflowValidation.test.ts`; UAT negative publish and governance panel screenshot. |
| `TOOL_CALL` | MCP/API resource, server IDs, tool name, schema mapping, timeout, retry, error behavior, allow-write policy, and outputs affect validation/runtime/evidence. | `test_runtime_v2_tool_call_node.py`, `test_runtime_v2_core.py`, `test_publish_validation.py`; UAT negative publish and governance panel screenshot. |
| `EXECUTE_WORKFLOW` | Target workflow, mappings, output mappings, version snapshot, timeout/depth policy affect nested runtime and validation. | `test_runtime_v2_execute_workflow_published_snapshot.py`, `test_runtime_v2_published_version_targeting.py`, `test_workflow_publish_versions.py`; UAT version binding. |
| `AGENT_CALL` | Target agent, message/mappings/history/depth/timeout/output mappings affect runtime invocation or validation. | `test_runtime_v2_provider_backed_llm.py`, `test_agent_call_node.py`, `test_runtime_v2_error_routing.py`; SOP compatibility gate. |
| `TRANSFER_TO_HUMAN` | Queue, reason, priority, SLA, message, and resume payload affect runtime interruption/resume evidence. | `test_runtime_v2_safe_node_coverage_pack2.py`, `chatflow-transfer-to-human-node` focused coverage in frontend/e2e corpus, wide backend gate. |
| `CODE` | Language, code body, timeout, inputs, outputs, and error behavior affect sandbox execution and runtime evidence. | `test_runtime_v2_safe_node_coverage_pack2.py`, `test_runtime_v2_error_routing.py`; UAT debug screenshot shows handled error evidence. |
| `TEXT_PROCESS` | Operation/template/source/pattern/replacement/output config affects runtime output. | `test_runtime_v2_node_coverage_pack1.py`, `test_runtime_v2_safe_node_coverage_pack2.py`, wide backend gate. |
| `JSON_PARSE` | Source and field map affect parsed outputs and type validation. | `test_runtime_v2_node_coverage_pack1.py`, `test_runtime_v2_safe_node_coverage_pack2.py`, frontend node config tests. |
| `VARIABLE_AGGREGATION` | Groups, strategies, variables, defaults, and output types affect runtime aggregation or validation. | `test_runtime_v2_node_coverage_pack1.py`, frontend `nodeConfig`/`variableCatalog` tests, wide backend gate. |
| `VARIABLE_ASSIGN` | Scope/target/source/write mode affect variable scopes; `sys.*` writes are blocked. | `test_publish_validation.py`, `test_runtime_v2_node_coverage_pack1.py`, `chatflowDebugTimeline` variable snapshot tests. |
| `INTENT_RECOGNITION` | Input source, classifier mode, history, intents, fallback branch, and output fields affect runtime branch output or endpoint validation. | `test_runtime_v2_node_coverage_pack1.py`, `test_publish_validation.py`, wide backend gate. |
| `MESSAGE` | Content, stream settings, fallback mode, and output variable affect message events/output. | `test_chatflow_runtime_v2_spike.py`, `test_runtime_v2_node_coverage_pack1.py`, debug timeline frontend tests. |
| `QUESTION` | Question, answer type/options, resume behavior, timeout, and output schema affect WAITING checkpoint/resume. | `test_chatflow_runtime_v2_spike.py`, `test_runtime_v2_long_run_lifecycle.py`, SOP compatibility gate. |
| `HUMAN_INPUT` | Prompt, approval mode, assignee, input schema, and output variable affect checkpoint/resume payload. | `test_runtime_v2_node_coverage_pack1.py`, `test_runtime_v2_long_run_lifecycle.py`, wide backend gate. |
| `INFORMATION_COLLECTION` | Fields, collection key, extractor mode, max rounds, stream settings, and write targets affect collection state, variable writes, or validation. | `test_runtime_v2_node_coverage_pack1.py`, `test_publish_validation.py`, frontend validation/debug variable projection tests. |
| `END` | Output mode, output variable, declared output parameters, and final template determine terminal output. | Publish/version UAT, `test_workflow_publish_versions.py`, `test_runtime_v2_published_version_targeting.py`, wide backend gate. |

## Residual Non-Blocking Risks

- API/MCP publish-time readiness validates resource identity and core node contract; deep live health/schema probing remains runtime evidence rather than a blocking publish health check.
- In-app Browser plugin could not attach a new webview tab in this Codex session; UAT used real Chromium Playwright screenshots and the images were visually inspected.
- Phase 2 capabilities remain excluded: Loop/Batch, SQL/database nodes, visual/file/multimedia nodes, and Coze-grade advanced canvas operations.
