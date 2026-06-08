# Browser UAT - 090 Variable Assignment Official Semantics

Date: 2026-06-08
Reference: Huawei AgentArts variable assignment node manual, especially the target-memory-variable and operation-assignment behavior: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0084.html

## Result
- PASS: Existing arbitrary assignment target `flow.route` is no longer rendered as a valid configured writable target in the node panel.
- PASS: Assignment target remains readonly and must be selected through the target picker.
- PASS: Assignment value still uses the split literal/reference control and can clear a selected upstream variable chip.
- PASS: Backend supports minimal operation assignment for scoped numeric variables; `conversation.score=7` plus operand `3` renders `score=10`.

## Evidence
- RED UI: red-ui.txt failed on old arbitrary target display.
- RED integration: red-integration.txt failed because operation assignment rendered empty score.
- E2E: e2e-assignment.txt passed with screenshot `screenshots/assignment-official-semantics.png`.
- Integration: integration.txt passed.
- Unit/rem: rem-unit.txt and full-unit.txt passed.
- Build: build.txt passed.
