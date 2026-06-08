# UAT

- Date: 2026-06-08
- Browser: Playwright Chromium, 1440x900 viewport.
- Reference basis: AgentArts task/chat workflow distinction plus Coze Studio node type/source audit.
- Workflow canvas: opened `/workflows/create`, clicked bottom `添加节点`.
  - Verified task workflow palette keeps `大模型`, `插件`, `工作流`, `API 调用`, `代码`, `选择器`, `意图识别`, `文本处理`, `JSON 解析`, `变量聚合`, `变量赋值`, `人工输入`, `知识库检索`.
  - Verified task workflow palette hides conversation-only entries `消息`, `问题`, `信息收集`, `转人工`.
  - Verified task workflow palette keeps `智能体`, because Hify `AGENT_CALL` is runtime-backed for both Workflow and Chatflow.
  - Screenshot: `screenshots/workflow-node-palette.png`.
- Chatflow canvas: opened `/chatflows/create`, clicked bottom `添加节点`.
  - Verified chatflow palette includes conversation entries `消息`, `问题`, `信息收集`, `转人工`, and `智能体`.
  - Screenshot: `screenshots/chatflow-node-palette.png`.
- In-app browser note: the current thread browser bridge exposed no attached page contexts, so UAT was performed with Playwright Chromium and saved screenshots.

Gate result: PASS.
