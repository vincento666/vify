# Browser UAT Notes

The in-app browser was opened on `http://localhost:4174/ai-assistant`, with the
FastAPI backend running on `http://127.0.0.1:8000`.

After running a real OpenRouter `qwen/qwen3.5-27b` message in session 44, run 88
completed with file read, knowledge search, skill intent, file write, and
readback tool calls.

Observed folded header:

```json
{
  "text": "已处理思考 3 次 / 文件操作 3 次 / 工具调用 2 次"
}
```

Observed expanded event headers:

```json
[
  "思考过程",
  "已读取 2 个文件",
  "工具调用",
  "已编辑 1 个文件",
  "已读取 1 个文件",
  "思考过程",
  "工具调用",
  "思考过程"
]
```

Observed detail assertions:

```json
{
  "hasReadDetail": true,
  "hasEditDetail": true,
  "hasKnowledgeInput": true,
  "hasSkillInput": true,
  "hasSkillOutput": true,
  "leaksSkillEquals": false,
  "leaksSkillRawTitle": false
}
```

Residual visual risk:
The live run produced two non-file tool groups because the harness had both
model-planned and supplement-injected knowledge/skill calls. The UI now groups
each contiguous non-file segment into one summarized invocation, while file
operations are separated into their own top-level file echo nodes.
