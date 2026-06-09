# 025.6 Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5173/chatflows/1730/canvas`

Verified:

- Default endpoint state captured.
- Selected node endpoint scales to `1.2x`.
- Selected node card uses an inset highlight.
- Node hover endpoint scale `1.2x` and direct endpoint hover scale `1.5x` passed in the real-browser Playwright gate.

Screenshots:

- `screenshots/uat-default-endpoint.png`
- `screenshots/uat-selected-endpoint.png`
- `screenshots/uat-playwright-endpoint-default.png`
- `screenshots/uat-playwright-endpoint-node-hover.png`
- `screenshots/uat-playwright-endpoint-endpoint-hover.png`
- `screenshots/uat-playwright-endpoint-selected.png`

Note:

The in-app browser CUA move channel did not trigger CSS `:hover`, although click/selected state worked. Hover states were therefore verified with the Playwright browser gate and phase screenshots.
