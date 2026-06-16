# Tasks 022: Customer Service Runtime Parity

## 022.1 Capability conformance inventory

- [x] RED: add failing conformance tests that expose uncovered current behavior.
- [x] Add tests proving Workflow `EXECUTE_WORKFLOW` still invokes a published Workflow and records nested run output.
- [x] Add tests proving Agent RAG calls `KnowledgeFacade` and includes references.
- [x] Add tests proving Agent native function/tool calling performs model-tool-model execution.
- [x] Add tests proving Workflow/Chatflow `KNOWLEDGE` node and LLM knowledge resource call `KnowledgeFacade`.
- [x] Record current gaps in `artifacts/slices/022-customer-service-runtime-parity/022.1/gap-audit.md`.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.1/`.
- [x] Gates pass.

## 022.2 Chatflow subworkflow conformance

- [x] RED: Chatflow `EXECUTE_WORKFLOW` integration test fails before coverage/guard work.
- [x] Add Chatflow fixture that calls a published child Workflow through `EXECUTE_WORKFLOW`.
- [x] Verify input mappings, output mappings, `nestedRunId`, and downstream variable references.
- [x] Add recursion and max-depth tests for Chatflow parent flows.
- [x] Add nested interrupt guard test: child Workflow returning `INTERRUPTED` is rejected with a clear error.
- [x] Ensure Chatflow session/checkpoint state remains owned by the parent Chatflow.
- [x] Add selected-node run test for Chatflow `EXECUTE_WORKFLOW`.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.2/`.
- [x] Gates pass.

## 022.3 Structured FAQ knowledge product

- [x] RED: FAQ model/API/retrieval tests fail.
- [x] Add `knowledge_faq` migration/model/repository.
- [x] Add optional FAQ embedding persistence or compatible fake embedding path.
- [x] Add FAQ CRUD APIs under knowledge base detail.
- [x] Add FAQ CSV import/export APIs.
- [x] Add source-aware retrieval DTO for FAQ and document chunks.
- [x] Keep backward-compatible `search_chunks()` or migrate callers through a compatibility adapter.
- [x] Merge exact, keyword, FAQ vector, and document chunk vector results deterministically.
- [x] Add Agent RAG integration test where FAQ answer is cited.
- [x] Add Workflow/Chatflow `KNOWLEDGE` node integration test where FAQ result is returned.
- [x] Add Knowledge frontend FAQ tab with CRUD.
- [x] Add Retrieval Test tab showing source type, match type, score, and content.
- [x] Add E2E: create FAQ, run retrieval test, use FAQ through Agent and Workflow.
- [x] Save Browser UAT screenshots for FAQ list, editor, import/export, and retrieval test.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.3/`.
- [x] Gates pass.

## 022.4 Agent tool-call hardening

- [x] RED: provider capability, write-policy, and evidence tests fail.
- [x] Add provider/model capability contract for native tool calling.
- [x] Block or warn when Agent tools are enabled on unsupported provider/model.
- [x] Add write-capable tool policy validation.
- [x] Normalize Agent tool-call evidence with call id, tool name, arguments summary, latency, status, and content summary.
- [x] Show tool-call evidence in Agent preview/debug panel and composer run debug detail.
- [x] Add integration tests for disabled tool, unsupported provider, timeout, and successful two-round call.
- [x] Add E2E: Agent with MCP tool produces final answer and visible tool evidence.
- [x] Save Browser UAT screenshots for supported, unsupported, success, and failure states.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.4/`.
- [x] Gates pass.

## 022.5 `AGENT_CALL` node

- [x] RED: backend executor and frontend schema tests fail for missing `AGENT_CALL`.
- [x] Add `AGENT_CALL` node type, labels, icon, default config, output parameters, and variable catalog support.
- [x] Add config panel sections: target Agent, input/message mapping, context/history, output mapping, policy, advanced.
- [x] Add Agent resource entries to Workflow resource registry.
- [x] Add `AgentInvocationFacade` and `AgentInvocationResult`.
- [x] Implement `AgentCallNodeExecutor`.
- [x] Implement Workflow and Chatflow run integration with nested agent evidence.
- [x] Implement recursion and max-depth guard across Agent and Workflow invocation.
- [x] Add selected-node run support.
- [x] Add Workflow integration test: `AGENT_CALL` maps input to Agent and maps output downstream.
- [x] Add Chatflow integration test: `AGENT_CALL` passes conversation context according to `historyMode`.
- [x] Add failure tests: missing Agent, disabled Agent, unsupported recursion, timeout.
- [x] Add E2E: add `AGENT_CALL`, configure target Agent, run node, use output downstream.
- [x] Save Browser UAT screenshots for node card, panel, run result, and debug evidence.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.5/`.
- [x] Gates pass.

## 022.6 Customer service end-to-end scenario

- [x] RED: full customer service E2E fails before wiring.
- [x] Build a seeded customer service Chatflow using intent, information collection, FAQ, tool call, subworkflow, Agent call, message, and transfer-to-human branch.
- [x] Publish the Chatflow to API/Web channel profile.
- [x] Invoke published run with a realistic support request.
- [x] Verify missing slot prompt, resume, FAQ answer, tool output, subworkflow output, Agent response, and handoff fallback.
- [x] Verify composer debug URL opens the owning Chatflow canvas debug dock.
- [x] Verify debug dock shows FAQ, tool, subworkflow, Agent, message, and handoff evidence.
- [x] Add Browser UAT recording for authoring, publish, run, resume, and debug inspection.
- [x] Save evidence under `artifacts/slices/022-customer-service-runtime-parity/022.6/`.
- [x] Gates pass.
