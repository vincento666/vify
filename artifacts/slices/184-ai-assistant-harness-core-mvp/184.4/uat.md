# 184.4 Browser UAT

Date: 2026-06-18

Target: `http://127.0.0.1:5173/ai-assistant`

Verified:

- AI Assistant shell renders in Hify's light content-area visual style.
- Left session list and run list are visible.
- Echo request renders center execution events and right inspector tool/task
  state.
- High-risk update request pauses with `approval.required` and renders an
  approval row in the right inspector.
- Event timeline remains inspectable on the right panel.
- No horizontal overflow at 1440 x 900 viewport.

Screenshot:

- `screenshots/ai-assistant-shell-e2e.png`
