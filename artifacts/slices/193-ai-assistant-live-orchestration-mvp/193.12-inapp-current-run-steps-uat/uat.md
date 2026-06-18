# 193.12 In-App Browser UAT

Date: 2026-06-18

Scope:
- Fix right-side execution steps so they are scoped to the current user question/run.
- Display model-planned tool steps only after planning exists.
- Use real tool/approval/run status for icons and animation.
- Keep completed steps as transparent green check icons; running steps use a spinner.

In-app browser target:
http://127.0.0.1:5173/ai-assistant

Journey:
1. Opened the Codex in-app browser and loaded the AI Assistant route.
2. Created a clean session, `会话 #37`.
3. Configured OpenRouter `qwen/qwen3.5-27b` through the UI with a temporary key.
4. Submitted a complex Chinese task requiring:
   - `read_workspace_file` for `specs/README.md`
   - `search_knowledge_base`
   - `invoke_skill`
   - `write_workspace_file` to `tmp/ai-assistant-inapp-current-run-steps.md`
   - approval before writing
5. Approved the write action in the UI.
6. Verified final answer, tool rows, approval history, right-panel execution steps, and one-screen layout.

Observed in-app browser summary:
- sampleCount: 31
- userMessageCount: 1
- sawRunningTaskAnimation: true
- sawStepSpinner: true
- approved: true
- finalHeader: 已处理45 条事件 / 4 次工具
- finalSteps: 5
- finalStepDoneCount: 5
- finalToolRows: 4
- badFinalStepTexts: []
- finalAnswers: 1
- pageOverflowY: 0

Final execution steps:
- 读取工作区文件已完成 / 工具调用 / 1 ms
- 知识库检索已完成 / 工具调用 / 0 ms
- 技能意图已完成 / 工具调用 / 0 ms
- 写入工作区文件已完成 / 工具调用 / 1 ms
- 写入工作区文件审批已批准 / 业务写入

Icon verification after CSS fix:
- each completed execution-step status icon background is `rgba(0, 0, 0, 0)`.
- each completed execution-step status icon color is green.
- each completed execution step exposes `ai-assistant-execution-step-done`.
- no completed execution step exposes the running spinner.

Screenshots:
- `screenshots/submitted.png`
- `screenshots/running-early.png`
- `screenshots/approved.png`
- `screenshots/completed.png`
- `screenshots/completed-icons-fixed.png`

Remaining risk:
- None for the current-run execution-step scope, state icon, and spinner behavior covered here.
