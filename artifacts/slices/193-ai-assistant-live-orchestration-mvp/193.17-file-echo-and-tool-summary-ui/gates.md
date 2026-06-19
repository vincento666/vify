# Gates

- Focused frontend unit:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts src/views/aiAssistant/aiAssistantShell.test.ts`
  passed, 33 tests.
- Focused frontend + remScaleClosure:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts src/views/aiAssistant/aiAssistantShell.test.ts src/remScaleClosure.test.ts`
  passed, 34 tests.
- Full frontend unit:
  `rtk npm --prefix frontend run test:unit`
  passed, 96 files / 416 tests.
- Frontend build:
  `rtk npm --prefix frontend run build`
  passed.
- AI Assistant backend gate:
  `rtk uv run pytest tests/unit/ai_assistant tests/integration/ai_assistant tests/contract/test_ai_assistant_observability_api.py tests/contract/test_ai_assistant_inspector_api.py tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_scheduler_api.py tests/contract/test_ai_assistant_live_qwen_api.py tests/contract/test_ai_assistant_live_stream_api.py tests/contract/test_ai_assistant_customer_bridge_api.py tests/contract/test_ai_assistant_session_lifecycle_api.py tests/contract/test_ai_assistant_security_api.py tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q`
  passed, 49 tests / 1 existing Starlette deprecation warning.
- Diff hygiene:
  `rtk git diff --check -- frontend/src/views/aiAssistant/aiAssistantTimeline.ts frontend/src/views/aiAssistant/aiAssistantTimeline.test.ts frontend/src/views/aiAssistant/AiAssistantShell.vue frontend/src/views/aiAssistant/aiAssistantShell.test.ts`
  passed.

## Browser UAT

- Browser target: `http://localhost:4174/ai-assistant`.
- Backend target: `http://127.0.0.1:8000`.
- Live model: OpenRouter `qwen/qwen3.5-27b`.
- Run: session 44 / run 88.
- Prompt asked the assistant to inspect harness file echo behavior, query
  knowledge, use TDD skill, write `tmp/ai-assistant-file-echo-uat.md`, read it
  back, and summarize in Chinese.
- Browser assertions:
  - Folded run header showed `思考 3 次 / 文件操作 3 次 / 工具调用 2 次`.
  - Expanded timeline showed top-level `已读取 2 个文件`, `工具调用`,
    `已编辑 1 个文件`, `已读取 1 个文件`.
  - File detail panels showed `输入/结果` with `路径`, `内容预览`, and write
    result text.
  - Tool details showed one summarized invocation per non-file group, with
    `知识库检索` and `使用技能` formatted as Chinese input/output rows.
  - Page text did not include `skill=tdd` or `技能调用`.
