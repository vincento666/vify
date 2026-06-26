# UAT — Slice 212.8

Date: 2026-06-26
Branch: codex/runtime-v2-production-upgrade

## Scenario
Open `chatflows/create`, fill `Chatflow 名称`, click 结束 node, set End-node
`output` template to `机器人收到 {{sys.query}} via {{sys.channel}} for
{{global.brand}}/{{global.locale}}`, open 对话试运行, expand profile fields,
send `查订单` with conversation/user defaults, wait for the assistant bubble.

## Expected
- `chatflow-assistant-message` testid resolves only to the COMPLETED bubble
  (loading bubble keeps `chatflow-assistant-loading` only).
- Assistant bubble innerText = `机器人收到 查订单 via web for Hify/zh-CN`.

## Observed
- `FINAL_TEXT: "机器人收到 查订单 via web for Hify/zh-CN"`
- Screenshot: `screenshots/green-conversation-run.png`

## Scope
Slice 212.8 fixes only L36 (assistant bubble empty content / testid timing).
E2E now advances past L36 / L40 / L45 / L49 / L52. New failure surfaces at
L58 (profile-grid `.run-input-field` controls all have height 0) — out of
scope for 212.8, recorded as 212.9 candidate.
