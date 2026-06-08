## 097 official node parity rerun

Date: 2026-06-09

### Official references checked

- Huawei Cloud AgentArts variable assignment: `https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0084.html`
  - Assignment target is constrained by placement: memory variables outside loops, loop intermediate variables inside loops.
  - Value source supports reference, input/fixed value, operation assignment, and clearing supported data types.
  - System references include conversation/history/user/time style parameters.
- Huawei Cloud AgentArts variable aggregation: `https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0085.html`
  - Aggregation returns the first non-empty value by configured priority.
  - Each group has same-type variables, default Group1, and output is derived from groups.
- Huawei Cloud AgentArts judgment/condition: `https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0066.html`
  - IF / ELSE IF / ELSE branches run in priority order.
  - Branch condition rows support AND/OR and type-specific operators.

### Fresh gates

- `unit-node-config-rerun.txt`: node config schema matrix passed.
- `e2e-condition-values-rerun.txt`: condition branch values/operators/variable picker passed.
- `e2e-condition-branch-endpoints-rebaseline.txt`: condition branch card endpoints stay aligned after endpoint rebaseline.
- `e2e-variable-aggregation-assignment-rerun.txt`: variable assignment and aggregation UI/runtime passed.
- `e2e-all-node-variable-audit-rerun.txt`: all node panels use the shared variable reference control.
- `e2e-resource-node-panels-rerun.txt`: tool/API/knowledge/subworkflow/agent resource panels passed.
- `e2e-chatflow-message-question-input-rerun.txt`: message/question/human input panels passed.
- `e2e-chatflow-information-collection-rerun.txt`: information collection panel passed.
- `e2e-chatflow-intent-recognition-rerun.txt`: intent recognition panel passed.
- `e2e-chatflow-transfer-to-human-rerun.txt`: transfer-to-human panel passed.
- `e2e-workflow-transform-nodes-rerun.txt`: code/text/JSON parse transform nodes passed.
- `e2e-api-resource-tool-builder-rerun.txt`: API resource and tool builder lite passed.
- `e2e-workflow-agent-call-rerun.txt`: agent call node passed.
- `e2e-workflow-execute-workflow-rerun.txt`: subworkflow node passed.
- `e2e-knowledge-faq-retrieval-rerun.txt`: knowledge retrieval runtime and UI passed.
- `e2e-palette-modes-rerun.txt`: workflow/chatflow palette split passed.
- `integration-core-structured-nodes-rerun.txt`: condition, transform, variable assignment/aggregation backend passed.
- `integration-resource-nodes-rerun.txt`: resource invocation backend passed.

### Current conclusion

- No node config schema exposes `高级/兼容配置`.
- Variable aggregation uses group cards, editable group headers, candidate rows, derived output rows, and no per-variable add button.
- Variable assignment uses target picker plus split literal/reference/operation value controls.
- Condition node uses branch-only config and branch card outputs/endpoints rather than generic input/output rows.
- Workflow palette and chatflow palette intentionally differ: task workflow hides conversation-only nodes, chatflow includes message/question/information collection/transfer/agent.
