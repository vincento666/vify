# 184.3 Browser UAT

Target: http://127.0.0.1:5173/ai-assistant

Services:

- Backend: `127.0.0.1:8000`
- Frontend: `127.0.0.1:5173`
- Database: MySQL8 on `127.0.0.1:3316`

Checks:

- AI Assistant route opens from the product shell.
- Core regions are present:
  - `ai-assistant-shell`
  - `ai-assistant-conversation-window`
  - `ai-assistant-event-stream`
  - `ai-assistant-composer`
  - `ai-assistant-send`
- Echo message `Please echo browser UAT event stream` creates 7 execution
  cards and includes `run.started`, tool output, and `run.completed`.
- High-risk message `please update customer profile tier to gold` creates
  `approval.required` and `proposed_action.created` cards with Approve/Deny
  controls.
- No `chain-of-thought` text appears in the visible UI.
- Screenshot saved:
  `artifacts/slices/184-ai-assistant-harness-core-mvp/184.3/screenshots/ai-assistant-execution-echo.png`

Visual notes:

- Center execution echo uses a dark console-style timeline with live status
  rail and card tones.
- Text and controls are visible without obvious overlap at the default browser
  viewport.
- Phase 3 will deepen the right task/run inspector and status animation.
