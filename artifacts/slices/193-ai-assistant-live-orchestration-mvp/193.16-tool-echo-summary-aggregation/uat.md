# Browser UAT

Target:
`http://localhost:4174/ai-assistant`

Source run:
Session `44`, run `87`, created by a real qwen3.5-27b complex UAT prompt that asked the assistant to read `specs/README.md`, search the knowledge base, invoke the TDD skill intent, write `tmp/ai-assistant-fuzzy-uat-2.md`, and read it back.

Steps:
1. Rebuilt frontend production assets.
2. Reloaded the in-app browser on `/ai-assistant`.
3. Verified the completed processed block header before expansion.
4. Expanded the processed block.
5. Expanded the single `工具调用` event.

DOM verification:
```json
{
  "processedHeaders": ["已处理思考 2 次 / 工具调用 1 次"],
  "eventHeaders": ["思考过程", "工具调用", "思考过程"],
  "toolHeaderCount": 1,
  "panelHasRead": true,
  "panelHasSearch": true,
  "panelHasSkill": true,
  "panelHasWrite": true,
  "panelHasInput": true,
  "panelHasOutput": true,
  "waitingResultCount": 0,
  "notFoundCount": 1
}
```

Result:
The visible execution echo no longer renders repeated `工具调用` nodes for each low-level `tool.call_output`. One summarized tool event remains, and its detail panel keeps readable per-tool input/output evidence. Completed empty outputs render concrete status such as `未找到` instead of `等待结果`.
