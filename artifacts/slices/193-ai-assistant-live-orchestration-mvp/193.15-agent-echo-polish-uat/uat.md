193.15 browser UAT evidence

Target: `http://127.0.0.1:5173/ai-assistant`

Real-model journey:

- Model: OpenRouter `qwen/qwen3.5-27b`
- User journey: create session, configure temporary model settings, send a
  colloquial complex task covering file read, knowledge-base search, tdd skill
  intent, workspace write, approval, and readback verification.
- Artifacts:
  - `complex-progress-uat.json`
  - `screenshots/progress-running-early.png`
  - `screenshots/progress-before-approval.png`
  - `screenshots/progress-completed.png`

Final UAT summary:

```json
{
  "sawTaskRows": true,
  "sawRunningTask": true,
  "sawAnimatedRunningTask": true,
  "sawStepSpinner": true,
  "finalHeader": "已处理思考 1 次 / 工具调用 4 次",
  "finalToolRows": 5,
  "finalAnswers": 1,
  "hasHashSequence": false,
  "pageOverflowY": 0,
  "finalToolTexts": [
    "读取工作区文件已完成 / 2 ms",
    "知识库检索已完成 / 1 ms",
    "技能意图已完成 / 1 ms",
    "写入工作区文件已完成 / 1 ms",
    "读取工作区文件已完成 / 1 ms"
  ]
}
```

Additional geometry check after expanding the completed task record:

```json
{
  "headers": ["思考过程", "工具调用", "工具调用", "工具调用", "工具调用"],
  "hasHashSequence": false,
  "parentCenterX": 466.8125,
  "childCenterXs": [466.8125, 466.8125, 466.8125, 466.8125, 466.8125],
  "maxDelta": 0,
  "eventCount": 5,
  "pageOverflowY": 0
}
```

Remaining risk:

- Codex in-app browser MCP did not expose a stable control tool in this turn, so
  UAT used real Playwright Chromium against the same local URL. The product page
  and backend service were the same ones used by the in-app browser.
