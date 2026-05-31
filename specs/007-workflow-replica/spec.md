# Spec 007: Workflow Replica

## Goal

Replicate workflow storage and synchronous execution: START, LLM, CONDITION,
KNOWLEDGE, API_CALL, END nodes, run records, and node-run records.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 007.1 Workflow CRUD | User can create/list/detail/update/delete workflow graph | RED: route contract fails; Unit: schema parsing; Integration: DB graph; E2E: workflow pages; UAT: graph persists |
| 007.2 Execution context | Template variables resolve as `{{node.var}}` | RED: context tests fail; Unit: variable pool; Integration: N/A; E2E: N/A; UAT: dev note |
| 007.3 Linear execution | START -> LLM/API/KNO -> END returns output and records run | RED: execution tests fail; Unit: executors; Integration: DB run rows; E2E: bound chat workflow; UAT: output appears |
| 007.4 Condition branching | CONDITION selects matching edge or default edge | RED: branch tests fail; Unit: branch picker; Integration: run records; E2E: workflow branch; UAT: branch result visible |
| 007.5 Safety/failure behavior | Missing START, unknown node, or >50 steps fails cleanly | RED: negative tests fail; Unit: safety checks; Integration: failed run recorded; E2E: error display; UAT: user sees error |

## Compatibility Rules

- Execution remains synchronous in replica phase.
- Node type strings preserve current Java values.
- Run and node-run records are best-effort but must not hide execution failure.
