## UAT

- Page: `/chatflows/create`.
- Header: `对话设置` keeps a lightweight settings icon; history retention controls are not inline by default.
- Header layout: the history settings icon stays inside the left-panel header, while the collapse/return control is docked on the panel outer edge with visible spacing.
- Click `对话历史策略`: opens a floating panel anchored under the header, matching the HiAgent-like header-triggered settings behavior.
- Slider/input: `对话轮数保留` uses a range slider plus compact numeric input; slider and input stay synchronized.
- Semantics: default retention is `3`; `0` means no persisted history injection. LLM/history-enabled nodes can follow this global setting.
- Layout regression: collapsing the chatflow settings panel and opening the run panel keeps toolbar and nodes inside the available canvas; the right panel no longer covers END after fit.

Screenshots:

- `screenshots/history-popover-final.png`
- `screenshots/history-popover-header-actions-final.png`
- `screenshots/settings-collapse-cozeflow-reserve.png`
- `screenshots/left-panel-readonly-regression.png`

## Gates

- RED unit: `red-unit.txt`
- RED e2e: `red-e2e.txt`
- RED header overlap e2e: `red-header-actions-overlap.txt`
- RED integration attempt/failure evidence: `red-integration.txt`, `integration-history-retention.txt`
- Unit/rem: `unit-rem-final.txt`
- Unit/rem after header actions: `unit-rem-header-actions.txt`
- Full frontend unit: `full-unit-final.txt`
- Full frontend unit after header actions: `full-unit-after-header-actions.txt`
- Frontend build: `build-final.txt`
- Frontend build after header actions: `build-after-header-actions.txt`
- E2E history popover: `e2e-history-popover-final.txt`
- E2E history popover/header actions: `e2e-header-actions-final.txt`
- E2E settings collapse/layout regression: `e2e-settings-collapse-cozeflow-reserve.txt`
- E2E readonly variable regression: `e2e-left-panel-readonly-regression.txt`
- Backend integration: `integration-history-file-final-rerun.txt`
- Backend integration after header actions: `integration-after-header-actions.txt`
