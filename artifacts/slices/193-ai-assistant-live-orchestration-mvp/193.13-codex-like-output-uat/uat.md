# Slice 193.13 Browser UAT

Target: `/ai-assistant`

Model: OpenRouter `qwen/qwen3.5-27b`

Journey:
- Configure temporary OpenRouter model settings from the message composer.
- Send a live prompt that requires planning and tool usage.
- Observe task planning, thought/tool grouping, visible assistant stream output,
  and completion card actions.

Verified:
- Document scroll overflow is `0`; the shell stays within one screen.
- User message renders as `data-testid="ai-assistant-user-message"` with subtle
  fill and no border.
- Visible assistant content renders as peer-level
  `data-testid="ai-assistant-assistant-message"`.
- Only active nodes spin during execution.
- Completed execution rows use done icons, not running animation.
- Completion cards expose copy, like, and dislike actions.

Screenshots:
- `artifacts/slices/193-ai-assistant-live-orchestration-mvp/193.13-codex-like-output-uat/screenshots/ai-assistant-running-icons-complete.png`
