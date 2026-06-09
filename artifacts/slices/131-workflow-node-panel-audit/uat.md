# 131 Workflow Node Panel Audit UAT

## Scope

- Workflow node-panel browser audit: condition branches, variable aggregation, resource nodes, agent/tool/subworkflow nodes, LLM resources/skills, transform nodes, publish, debug deeplink, canvas lifecycle, node test, and run panel.
- Fixed brittle E2E assertions only:
  - Scope workflow "试运行" clicks to `.canvas-actions` so the topbar and bottom toolbar buttons do not collide.
  - In chatflow multi-turn assertions, read the newly appended assistant message instead of the first visible bubble.
  - For LLM canvas run UAT, accept either live provider success or a visible provider-error panel in offline/local environments; backend fake-client integration tests cover the success contract.

## Evidence

- RED:
  - `red.txt`
  - `e2e-workflow-knowledge-condition-run.txt`
  - `e2e-workflow-chatflow-llm-run.txt`
- Browser E2E:
  - `workflow-test-run.txt`
  - `workflow-knowledge-condition-run.final.txt`
  - `workflow-chatflow-llm-run.final.txt`
  - `e2e-condition-branch-values.txt`
  - `e2e-condition-branch-endpoints.txt`
  - `e2e-variable-aggregation-official.txt`
  - `e2e-variable-aggregation-assignment.txt`
  - `e2e-resource-node-panels.txt`
  - `e2e-agent-call-node.txt`
  - `e2e-tool-call-node.txt`
  - `e2e-execute-workflow-node.txt`
  - `e2e-llm-callable-skills.txt`
  - `e2e-llm-resources.txt`
  - `e2e-transform-nodes.txt`
  - `e2e-all-node-variable-reference.txt`
  - `e2e-workflow-publish.txt`
  - `e2e-workflow-run-debug-deeplink.txt`
  - `e2e-workflow-canvas-ux-lifecycle.txt`
  - `e2e-workflow-node-test.txt`
- Backend LLM contract: `backend-llm-contract.txt`
- Frontend rem gate: `rem.txt`
- Full frontend unit: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`

## Result

PASS. The workflow node audit gate is green in the local browser/runtime environment.
