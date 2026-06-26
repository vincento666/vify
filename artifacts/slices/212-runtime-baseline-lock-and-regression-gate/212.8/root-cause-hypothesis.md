# Root cause hypotheses for slice 212.8

## Hypothesis A — Backend not emitting tokens
Evidence: probe.log shows backend completes successfully with
`{"output":"机器人收到 查订单 via web for Hify/zh-CN"}` in events (sequence 5,7,8)
and in the final `/runtime-runs/6135` response.
Confidence: **rejected** (backend works correctly).

## Hypothesis B — Frontend SSE consumer / runtime v2 polling not rendering
Evidence: After polling, innerText shows the full expected text
(POLLED_INNER_TEXT). FINAL_LOADING_COUNT = 0, BUBBLE_INNERHTML contains
the rendered span with the full content. So consumer works, just not
immediately.
Confidence: **rejected** as direct cause.

## Hypothesis C — sys/global variable template not resolved
Evidence: probe shows output already contains the resolved string. Rejected.
Confidence: **rejected**.

## Hypothesis D — Race: testid `chatflow-assistant-message` is on the
LOADING bubble (loading dots, no text), so `waitFor({visible})` matches
immediately on the loading bubble; then `innerText` reads empty before
the assistant content arrives.

Evidence:
- IMMEDIATE_INNER_TEXT: ""
- POLLED_INNER_TEXT (after up to 8s polling): "机器人收到 查订单 via web for Hify/zh-CN"
- During loading: bubble has `data-testid="chatflow-assistant-message"`
  with a child `<span data-testid="chatflow-assistant-loading">` containing only
  three `<i aria-hidden>` (no text). Only after run completes, bubble content
  becomes the rendered text.
- WorkflowCreate.vue:3322 attaches `chatflow-assistant-message` unconditionally
  for assistant bubbles regardless of `message.loading`.

Confidence: **HIGH**. This is the chosen root cause.

## Chosen: D — testid contract leaks loading-state bubble as "assistant message"

## Verification
Make `chatflow-assistant-message` testid apply ONLY when the bubble has
arrived at a non-loading state. The loading bubble keeps its own
`chatflow-assistant-loading` testid (already on the child span). e2e
`waitFor({visible})` will then wait until the final bubble appears,
allowing `innerText` to read the resolved string.

## Compatibility check with existing e2e using chatflow-assistant-message
- chatflow-run-optimistic-loading.mjs: polls innerText on
  `getByTestId('chatflow-assistant-message')`; Playwright locator
  auto-waits until match exists. SAFE.
- chatflow-trial-chat-panel.mjs:99,127: counts/waits — fine after final
  bubble exists. SAFE.
- workflow-six-node-matrix.mjs / workflow-knowledge-condition-run.mjs:
  query final bubbles after run; SAFE.
- workflow-chatflow-llm-run.mjs / chatflow-stream-typewriter.mjs /
  workflow-canvas-ux-lifecycle.mjs / chatflow-conversation-run.mjs:
  expect the completed bubble; SAFE.
