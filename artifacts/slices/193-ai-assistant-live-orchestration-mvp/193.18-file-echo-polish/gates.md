# Gates

- Focused frontend unit:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts src/views/aiAssistant/aiAssistantShell.test.ts`
  passed, 34 tests.
- Focused frontend + remScaleClosure:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantTimeline.test.ts src/views/aiAssistant/aiAssistantShell.test.ts src/remScaleClosure.test.ts`
  passed, 35 tests.
- Full frontend unit:
  `rtk npm --prefix frontend run test:unit`
  passed, 96 files / 417 tests.
- Frontend build:
  `rtk npm --prefix frontend run build`
  passed.
- Diff hygiene:
  `rtk git diff --check -- frontend/src/views/aiAssistant/aiAssistantTimeline.ts frontend/src/views/aiAssistant/aiAssistantTimeline.test.ts frontend/src/views/aiAssistant/AiAssistantShell.vue frontend/src/views/aiAssistant/aiAssistantShell.test.ts`
  passed.

## Browser UAT

- Browser target: `http://localhost:4174/ai-assistant`.
- Existing live run inspected: session 44 / run 88.
- Folded `已处理` header showed `思考 3 次 / 工具调用 2 次` with no file
  operation count.
- Expanded file detail panels no longer contained both `读取：`/`编辑：` and
  `路径：` for the same item.
- Repeated readback of `tmp/ai-assistant-file-echo-uat.md` showed one path block.
- Tool child headers showed `知识库检索、使用技能` instead of `工具调用`.
