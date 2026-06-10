# 156 Node Actions, Streaming Switches, Run Validation, Debug Detail UAT

Date: 2026-06-10

## In-App Browser UAT

- `workflows/create` invalid graph: clicking toolbar run opens `错误列表`, keeps `test-run-panel` closed.
- Workflow node cards: `START`/`END` cards expose no top-right action buttons; LLM card exposes run/more icon buttons with transparent background and no border.
- LLM config panel: `流式输出` switch is visible and config title edit button is present.
- Agent config panel: `流式输出` switch is visible.
- Debug dock: selected LLM node detail shows `输入` with `runtimeInput.USER_INPUT`, rendered prompt, and `输出.answer`.

Screenshots:

- `screenshots/in-app-validation-errors.png`
- `screenshots/in-app-llm-panel-actions.png`
- `screenshots/in-app-agent-stream-switch.png`
- `screenshots/in-app-debug-node-input-output-selected.png`

## Notes

- AgentArts official code-node documentation explicitly uses fixed entry functions (`def main(args: dict) -> dict`, `exports.main = async (event, context) => {}`) and shows `args.get("input")` in Python examples.
- Coze public code-node page is client-rendered in the browser; this slice treats the implemented code-node semantics as AgentArts-compatible fixed entry plus Coze-like input/output parameter behavior, not as a claimed verbatim Coze `args.get` signature.
- Current streaming is event/typewriter preview after node completion, not true provider token SSE. LLM and Agent panels now expose `streamOutput`; Agent runtime emits `agent_delta` preview events when enabled/inherited.
