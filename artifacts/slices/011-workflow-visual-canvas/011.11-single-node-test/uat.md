# 011.11 Browser UAT

Date: 2026-06-02

## Coze Reference

- The selected-node test UX follows the live-audit target captured in `specs/011-workflow-visual-canvas/spec.md`: right-panel header run action, input fixture area, running/success states, `查看日志`, `运行结果`, `输入`, `推理内容`, `技能调用`, and `输出`.
- Direct Coze live-page automation was still unstable in this environment, so this slice uses the existing Coze live-audit artifacts plus local browser execution evidence.

## Local Browser UAT

Local URL used: `http://127.0.0.1:15182/workflows/567/canvas`

Validated in the Codex in-app browser:

- Created a `开始 -> 大模型 -> 结束` workflow where END would add a visible `DOWNSTREAM` prefix if full-flow execution continued.
- Selected the LLM node.
- Clicked the right-panel header `试运行当前节点` icon.
- Drawer opened with `试运行输入`, `JSON模式`, disabled `AI 补全`, and a `userMessage` input row.
- Entered `来自浏览器的节点单测`.
- Clicked the drawer `运行` button.
- Result showed `SUCCEEDED`, elapsed time, `输入`, `推理内容`, `技能调用`, and `输出`.
- Output was `节点试运行通过，引用输入：来自浏览器的节点单测`.
- The result did not include `DOWNSTREAM`, confirming the selected-node path did not continue into END.

## Evidence

- `red.txt`: RED failures showed `WorkflowService.run_node` and `/nodes/{node_key}/runs` did not exist.
- `unit.txt`: selected-node service tests passed.
- `integration.txt`: selected-node API tests passed.
- `frontend-unit.txt`: frontend workflow unit tests passed.
- `frontend-build.txt`: production frontend build passed.
- `e2e.txt`: selected-node drawer E2E passed.
- Screenshots:
  - `screenshots/e2e-node-test.png`
  - `screenshots/browser-uat-node-panel.png`
  - `screenshots/browser-uat-node-drawer-idle.png`
  - `screenshots/browser-uat-node-drawer-success.png`

## Verdict

Pass. The panel header action now runs only the selected node and displays node-only input, reasoning/output, skill-call state, and success/error surface.
