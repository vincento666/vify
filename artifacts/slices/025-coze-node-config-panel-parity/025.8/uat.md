# 025.8 Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5176/chatflows/1868/canvas`

## Result

PASS. The in-app browser opened a dedicated Chatflow containing `MESSAGE`, `QUESTION`, `INFORMATION_COLLECTION`, and `INTENT_RECOGNITION` nodes.

Verified panels:

- `MESSAGE`: shows `发送消息`, `发送内容`, `流式输出`, and output rows.
- `QUESTION`: shows `提问并等待`, `回答选项`, and two structured option rows.
- `INFORMATION_COLLECTION`: shows `收集策略`, `收集字段`, `写入会话上下文`, and two structured collection field rows.
- `INTENT_RECOGNITION`: shows `识别策略`, `意图分支`, and two structured intent rows.

Screenshots:

- `uat-message-panel.png`
- `uat-question-panel.png`
- `uat-information-collection-panel.png`
- `uat-intent-panel.png`

Notes:

- At the default narrow in-app browser viewport, the right config panel can cover far-right canvas nodes. UAT used the actual narrow path by closing the current config panel before selecting the next covered node.
- Full machine-readable UAT details are in `uat-browser.json`.
