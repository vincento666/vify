# 102 Variable Aggregation, Assignment, And Node Catalog Current Gate

- Date: 2026-06-09
- Scope: current variable aggregation, variable assignment, and workflow/chatflow palette separation evidence.

## Evidence

- `unit-node-config.txt`: node config schema tests pass for structured aggregation/assignment panels and no advanced compatibility sections.
- `e2e-aggregation-official.txt`: variable aggregation panel matches the official first-non-empty grouped model.
- `e2e-aggregation-assignment.txt`: workflow and chatflow variable aggregation/assignment runtime and panel paths pass.
- `unit-node-palette-current.txt`: node palette mode filtering unit tests pass.
- `e2e-node-palette-current.txt`: workflow/chatflow palette mode E2E passes.

## Product Decision

Workflow hides conversation-only nodes (`消息`, `问题`, `信息收集`, `转人工`). `智能体` stays available in both Workflow and Chatflow because Hify has a runtime-backed `AGENT_CALL` node for both modes.
