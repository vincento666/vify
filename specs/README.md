# Hify Spec Index

Specs are executed by the current natural execution order below. Directory
numbers are stable historical IDs and should not be renamed once evidence paths
or references exist.

Each spec is split into vertical slices, and each slice must pass the gates
defined in `docs/testing/acceptance-gates.md` before the next slice starts.

## Current Natural Execution Order

| Order | Spec / Slice | Purpose |
|-------|--------------|---------|
| 1 | 000-020 in numeric order | Foundation, Workflow/Chatflow canvas, Agent workbench, core nodes, resources, state, publish, and evaluation baseline |
| 2 | 025.1-025.4 | Fix the core authoring loop first: variable references, Start panel, End panel, and LLM panel high-fidelity Coze alignment |
| 3 | 025.5-025.7 | Finish core canvas usability: running path/active branch animation, endpoint hover/selection affordances, and midpoint edge insert quick-connect |
| 4 | 021 remaining slices, especially 021.12 | Composer-embedded run/debug detail and publish/Open API/debug IA cleanup after the authoring surface is usable |
| 5 | 024.1-024.2 | Streaming/typewriter output and node-level token/cost/runtime evidence that feed the debug experience |
| 6 | 022 remaining slices, if any | Customer-service runtime parity: Knowledge, Tool, Subworkflow, Agent Call, and structured FAQ capabilities |
| 7 | 024.3-024.4 | API Resources, Tool Builder Lite, and multi-channel publish profiles |
| 8 | 025.8-025.10 | Secondary Chatflow panels, resource node panels, and data/structured node editors after their runtime/resource capabilities are stable |
| 9 | 023 | Integration architecture deepening and consolidation before the next broad expansion wave |
| 10 | 026 | Workflow/Chatflow polish hardening for layout, lists, shared controls, config panels, and variable selectors |
| 11 | 027 | Workflow/Chatflow config hardening for Start defaults, variable references, selectors, branches, and icon polish |
| 12 | 035 | Productize Knowledge retrieval strategy, FAQ vector recall, vector-store adapters, and lifecycle UX |
| 13 | 045-046 | Customer-assistant runtime MVP and operator panel baseline |
| 14 | 047-052 | Customer-assistant actor persistence, live L1 events, restricted worker, proposed actions, eval data, and harness-compatible sub-agent contract |
| 15 | 053-058 | Runtime v2 alignment, synthetic eval/LLM promotion, operator-turn mode, worker hardening, and Chatflow-first v2 transport spike |
| 16 | 059, 060, 061 | Real customer-assistant worker async runtime, MySQL8/Weaviate persistence readiness where required, and async worker orchestration |
| 17 | 062-066 | Shared Hify Workflow/Chatflow runtime v2 core, Chatflow facade, deterministic node pack, Workflow facade, and async Chatflow SOP worker adapter |
| 18 | 067-069 | Cross-runtime observability gate, restricted ReAct worker standardization, and smooth Two-Stage ReAct customer-assistant runtime |
| 19 | 070 | Realtime control or scale-out transport only after SSE/durable polling is proven insufficient |
| 20 | 212-221 | Chatflow/Workflow production runtime upgrade per `docs/chatflow-workflow-production-upgrade.md` |
| 21 | 222 | Generic AI Assistant harness MVP, live LLM real-case UAT, and corrective runtime hardening |
| 22 | 224 | Durable AI Assistant ToolRunner idempotency ledger and circuit breaker semantics |
| 23 | 188.4-188.5, 190.3, 188.6-188.7, then 190.4-190.6 | Replace legacy AI Assistant memory with scoped MEMORY.md, add model-call accounting before extraction, then ship aggregates and dashboard |
| 24 | 225-workflow-chatflow-control-hardening | Corrective Workflow/Chatflow authoring control hardening after reproducible toolbar, drag, and config-panel regressions |
| 25 | 225-runtime-lab-sop-live-stream | RuntimeLab SOP async-first live stream bridge over Chatflow Runtime V2, including genuine provider chunks and reconnectable UI projection |
| 26 | 226-ai-assistant-runtime-convergence-shell | Converge AI Assistant on the domain-neutral durable runtime job substrate, harden trusted execution identity, and ship the Hify-light collapsible activity shell with real subagent presence |
| 27 | 228-runtime-policy-replay-and-uncertainty | Repair evaluation truth and enforce classifier uncertainty before any RuntimeLab mutation |
| 28 | 229-runtime-lab-intent-routing-reliability | Fuse candidates, add margin/context, and isolate a versioned intent catalog and retriever |
| 29 | 230-runtime-route-execution-boundary | Separate route proposals from trusted execution authority and child side-effect permission |
| 30 | 231-runtime-lab-composite-intent | Preserve, clarify, and explicitly resolve bounded multi-intent turns without silent flattening |

## Directory Index

| Spec | Purpose |
|------|---------|
| 000-current-boundary-inventory | Freeze current API, schema, mock behavior, and known gaps |
| 001-backend-foundation | FastAPI backend skeleton and shared infrastructure |
| 002-frontend-foundation | Frontend compatibility and one-command local startup |
| 003-provider-management | Provider/model/health management replica |
| 004-agent-management | Agent CRUD and tool/model binding replica |
| 005-chat-engine | Chat session, sync chat, SSE streaming, context cache |
| 006-knowledge-mock-replica | Current knowledge-base mock behavior replica |
| 007-workflow-replica | Workflow persistence and execution engine replica |
| 008-mcp-replica | MCP server CRUD, connection test, tools/debug replica |
| 009-real-rag-pgvector | Replace knowledge mock with real pgvector RAG |
| 010-real-tool-calling-and-mcp | Real OpenAI tool calling and MCP execution integration |
| 011-workflow-visual-canvas | Visual draggable workflow canvas for current node/runtime boundary |
| 012-chatflow-visual-canvas | Chatflow list/canvas/profile that reuses workflow graph/runtime |
| 013-evaluation-loop-replica | Coze Loop-inspired Evaluation workbench; MVP is an Agent-only eval set, deterministic evaluator, experiment run, and report loop |
| 014-agent-workbench-mvp | Product-level single-Agent Workbench; MVP-first implementation, then publishing, versions, memory, variables, tool policy, RAG settings, evaluation gates, sharing, and analytics |
| 015-core-flow-nodes-mvp | Next MVP nodes for data transform, variables, intent, message/question/input, and smart information collection |
| 016-frontend-rem-scale-governance | Global REM scale governance for Hify frontend, adapted from vifly-experiment continuous desktop scale |
| 017-resource-tool-subworkflow-runtime | Runtime-backed plugins/tools, LLM callable skills, and explicit subworkflow invocation for Workflow/Chatflow |
| 018-chatflow-interrupt-session-state | Chatflow sessions, scoped variables, events, checkpoints, and single-flow interrupt/resume |
| 019-human-handoff-channel-publish-observe | Chatflow transfer-to-human, Web/API channel publishing, versioned release, and observe surfaces |
| 020-coze-grade-evaluation-replica | Deepen 013 Evaluation into Coze-grade Eval Set versions/columns, Experiment stepper/mapping, and Evaluator Workbench v2 |
| 021-coze-composer-run-debug-refactor | Refactor global Observe into Coze Studio-style embedded Workflow/Chatflow/Agent run debugging and debug URL deep links |
| 022-customer-service-runtime-parity | Close customer-service runtime gaps: Chatflow subworkflow conformance, structured FAQ, Agent tool-call hardening, and explicit AGENT_CALL node |
| 023-integration-architecture-deepening | Deepen host integration, access policy, runtime evidence, FlowGraph node catalog, resource invocation, evaluation targets, conversation runtime, and persistence lifecycle for low-coupling system embedding |
| 024-runtime-streaming-resource-channel-mvp | Ship high-priority runtime product gaps: Chatflow streaming/typewriter, node usage/cost evidence, API Resources with Tool Builder Lite, and compatible channel profile adapters |
| 025-coze-node-config-panel-parity | Prioritize Coze-like Start/End/LLM panels and variable reference controls, then harden running-path, endpoint, and edge-insert canvas interactions |
| 026-workflow-chatflow-polish-hardening | Harden Workflow/Chatflow layout, lists, shared controls, config panels, and variable selector polish |
| 027-workflow-chatflow-config-hardening | Harden Start defaults, variable references, floating selectors, branch conditions, and workflow icon buttons |
| 028-workflow-chatflow-input-picker-model-hardening | Harden variable-reference input pickers and LLM model/parameter controls |
| 029-isolated-runtime-router-lab | Isolated runtime router lab for safer routing experiments |
| 030-runtime-semantic-routing-arbitration | Semantic routing arbitration for runtime decisions |
| 031-chatflow-sop-adapter-contract | Adapter contract for Chatflow-backed SOP execution |
| 032-chatflow-sop-integration | Real Chatflow SOP integration through the adapter contract |
| 033-runtime-fallback-policy | Runtime handoff and fallback policy foundation |
| 034-unified-routing-chat-lab | Unified routing chat lab across direct and fallback paths |
| 035-knowledge-retrieval-productization | Productize Knowledge retrieval with selectable recall modes, FAQ vectorization, adapter boundaries, and lifecycle UX |
| 036-runtime-faq-exact-answer-gate | Exact FAQ answer gate for runtime fallback paths |
| 037-runtime-faq-embedding-answer-gate | Embedding-based FAQ answer gate for runtime fallback paths |
| 038-runtime-rag-answer-gate | RAG answer gate for runtime fallback paths |
| 039-runtime-controlled-agent-fallback | Controlled agent fallback with policy boundaries |
| 040-runtime-fallback-e2e-lab-acceptance | E2E and lab acceptance for runtime fallback behavior |
| 041-runtime-policy-config-observability | Runtime policy configuration and observability |
| 042-runtime-policy-release-governance | Runtime policy release governance |
| 043-frontend-module-capsule-adapter-refactor | Frontend module capsule adapter refactor |
| 044-frontend-ant-design-vue-migration | Frontend migration to Ant Design Vue |
| 045-customer-assistant-runtime-mvp | ToB customer-assistant runtime MVP with task ledger and parallel workers |
| 046-customer-assistant-operator-panel-mvp | Customer-assistant operator panel MVP in the main menu |
| 047-customer-assistant-llm-shadow-and-actor | Actor persistence and opt-in LLM shadow mode for customer assistant |
| 048-customer-assistant-live-l1-events-sse | True execution-time L1 customer-assistant events over SSE |
| 049-customer-assistant-restricted-react-worker | Restricted task-bound ReAct worker for customer assistant |
| 050-customer-assistant-proposed-action-execution-lifecycle | Proposed-action confirmation and mock execution lifecycle |
| 051-customer-assistant-eval-data-foundation | Evaluation data path and initial golden cases for customer assistant |
| 052-customer-assistant-harness-compatible-sub-agent | Harness-compatible eventful customer-assistant sub-agent contract |
| 053-workflow-chatflow-runtime-v2-event-alignment | Workflow/Chatflow runtime v2 event and async lifecycle alignment |
| 054-customer-assistant-synthetic-eval-and-llm-promotion | Synthetic eval, Chatflow/SOP data readiness, and LLM promotion gate |
| 055-customer-assistant-llm-primary-path-mvp | Opt-in customer-assistant LLM primary path with deterministic fallback |
| 056-customer-assistant-worker-runtime-hardening | Worker timeout, cancellation, and async ref hardening for customer assistant |
| 057-customer-assistant-operator-turn-mode | Operator recommendation-only turn mode and proposed task command flow |
| 058-realtime-runtime-transport-and-workflow-chatflow-v2-spike | Realtime transport decision and Chatflow-first runtime v2 spike |
| 059-customer-assistant-worker-async-runtime-mvp | Durable async runtime for one customer-assistant worker path |
| 060-mysql8-weaviate-demo-migration | Demo migration to MySQL8 primary DB plus Weaviate vector store |
| 061-customer-assistant-async-worker-orchestration | Customer-assistant task orchestration over real async worker refs |
| 062-hify-workflow-chatflow-shared-runtime-v2-core | Shared runtime v2 core for Hify Workflow and Chatflow |
| 063-hify-chatflow-runtime-v2-facade-mvp | Chatflow facade over the shared Hify runtime v2 core |
| 064-hify-runtime-v2-core-node-coverage-pack-1 | First deterministic node coverage pack for Hify runtime v2 core |
| 065-hify-workflow-runtime-v2-facade-mvp | Hify Workflow facade over the shared runtime v2 core |
| 066-customer-assistant-async-chatflow-sop-worker-adapter | Customer-assistant Chatflow SOP worker using Chatflow v2 when compatible |
| 067-cross-runtime-observability-and-regression-gate | Cross-runtime observability and regression gate across assistant, workers, and Hify runtime v2 |
| 068-restricted-react-worker-runtime-standardization | Standardized bounded ReAct worker runtime with tool policy and events |
| 069-customer-assistant-two-stage-react-runtime-mvp | Smooth opt-in Two-Stage ReAct runtime for customer assistant |
| 070-realtime-control-and-scale-out-transport | Late-stage realtime control and scale-out transport decision/spike |
| 188-ai-assistant-prompt-skills-memory-compaction | Scoped per-user/workspace MEMORY.md with 30-day bounded reads and three-successful-run model extraction |
| 190-ai-assistant-observability-benchmark | Per-model-call token/cost ledger, scoped aggregates, and AI Assistant usage dashboard; no benchmark expansion |
| 194-workflow-chatflow-productionization-phase1 | Productionize current text Workflow/Chatflow core nodes through runtime v2, unified error routing, API/Tool governance, validation, version snapshots, and UAT evidence |
| 212-runtime-baseline-lock-and-regression-gate | Lock baseline & regression gate per upgrade doc §4 |
| 213-runtime-async-default-invocation-gateway | Async-first runtime invocation gateway §5 |
| 214-runtime-dag-multipath-semantics | DAG edge/port/branch/skipped/terminal/final-output semantics §6 |
| 215-runtime-dag-frontier-scheduler | Frontier-based DAG scheduler with concurrency and failure strategies §7 |
| 216-chatflow-sop-compat-on-dag | Chatflow & SOP compatibility on DAG runtime, SOP ledger boundary §8 |
| 217-runtime-v2-node-compatibility-matrix | Node compatibility matrix and side-effect node idempotency §9 |
| 218-runtime-production-job-scheduler | Production-grade job claim, lease, retry, DLQ and standalone worker §10 |
| 219-runtime-event-cancel-ratelimit-backpressure | Event stream reliability, cancel, multi-level rate limit and backpressure §11 |
| 220-runtime-observability-ops-module | Runtime Ops main-menu module with run/job/DLQ panels and safe ops actions §12 |
| 221-runtime-capacity-fault-acceptance | Capacity & fault acceptance with chaos drills and capacity report §13 |
| 222-ai-assistant-general-harness-mvp | Generic AI Assistant harness MVP with first-class planning, streaming, tools, workspace, session recovery, policy, memory, skills, audit, live LLM real-case UAT, and corrective runtime hardening |
| 224-ai-assistant-durable-toolrunner-idempotency | Durable ToolRunner idempotency ledger, UNKNOWN lifecycle, fallback identity, and circuit breaker semantics |
| 225-workflow-chatflow-control-hardening | Corrective UI control geometry, honest structured-row drag, variable-scope audit, and lifecycle UAT for Workflow/Chatflow authoring |
| 225-runtime-lab-sop-live-stream | RuntimeLab SOP async-first SSE bridge to Chatflow Runtime V2 with genuine provider deltas and reconnectable UI projection |
| 226-ai-assistant-runtime-convergence-shell | Domain-neutral runtime job reuse, trusted AI execution identity, standalone HA worker, stable activity projection, Hify-light auto-collapse shell, real child presence, and evidence-based cleanup |
| 228-runtime-policy-replay-and-uncertainty | Shared production-path route replay, false-green protection, confidence/clarification enforcement, and targeted clarification |
| 229-runtime-lab-intent-routing-reliability | Canonical multi-source fusion, ambiguity margin, read-only route context, and isolated versioned intent retrieval |
| 230-runtime-route-execution-boundary | Trusted principal, pre-mutation gate, bounded confirmation, audit, and RuntimeLab-owned Runtime V2 effect authorization |
| 231-runtime-lab-composite-intent | Atomic component preservation, sequencing clarification, bounded pending route plans, and explicit composite resolution |

## Required Files Per Spec

```text
spec.md   # user value, behavior, slices, acceptance gates
plan.md   # implementation approach and architecture notes
tasks.md  # executable checklist with evidence links
```
