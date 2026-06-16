# Tasks 017: Resource Tool And Subworkflow Runtime

## 017.1 Resource registry and picker contract

- [x] RED: resource registry contract tests fail for enabled, disabled, unhealthy, and missing-credential resources.
- [x] Implement backend resource registry facade.
- [x] Implement frontend resource picker contract and status rendering.
- [x] Keep unsupported resources visible only as disabled or hidden according to spec.
- [x] Save evidence under `artifacts/slices/017-resource-tool-subworkflow-runtime/017.1/`.
- [x] Gates pass.

## 017.2 TOOL_CALL node

- [x] RED: TOOL_CALL node unit/integration tests fail.
- [x] Add node type, metadata, card, dynamic ports, and config panel.
- [x] Implement input mapping and output schema controls.
- [x] Implement `ToolCallNodeExecutor` with fake adapter first.
- [x] Persist sanitized resource call evidence in node run records.
- [x] Add E2E: add tool node, map input, run selected node, use output downstream.
- [x] Save evidence under `artifacts/slices/017-resource-tool-subworkflow-runtime/017.2/`.
- [x] Gates pass.

## 017.3 LLM callable skills

- [x] RED: LLM callable skill tests fail.
- [x] Add LLM skills config for runtime-backed tools.
- [x] Build provider-compatible tool schemas.
- [x] Implement one-round model-tool-model execution with fake adapter tests.
- [x] Guard unsupported provider/model capability.
- [x] Render tool call evidence in node-test drawer and debug dock.
- [x] Save evidence under `artifacts/slices/017-resource-tool-subworkflow-runtime/017.3/`.
- [x] Gates pass.

## 017.4 EXECUTE_WORKFLOW node

- [x] RED: subworkflow invocation tests fail.
- [x] Add node type, target workflow selector, input mapping, output mapping, and policy controls.
- [x] Implement nested run execution for published Workflow targets.
- [x] Add recursion/depth guard.
- [x] Persist parent/nested run links.
- [x] Add E2E: parent workflow invokes subworkflow and maps output downstream.
- [x] Save evidence under `artifacts/slices/017-resource-tool-subworkflow-runtime/017.4/`.
- [x] Gates pass.

## 017.5 Resource error and security policy

- [x] RED: timeout, retry, credential-missing, and unsafe-write tests fail.
- [x] Implement execution policy resolver.
- [x] Implement error branch/default behavior where configured.
- [x] Verify graph config never stores secrets.
- [x] Add UAT for disabled resource reason and run failure evidence.
- [x] Save evidence under `artifacts/slices/017-resource-tool-subworkflow-runtime/017.5/`.
- [x] Gates pass.
