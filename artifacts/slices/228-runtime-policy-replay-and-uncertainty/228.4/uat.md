# 228.4 Browser UAT

Date: 2026-07-26

Environment:

- real Vite frontend: `127.0.0.1:15173`
- real FastAPI + MySQL backend: `127.0.0.1:18080`
- deterministic artifact-only classifier harness:
  `browser_fixture_app.py`
- live / paid provider calls: `0`
- Browser: Codex in-app Chromium; real DOM interaction
- console errors: `0`

| Case | Visible result | State evidence | Verdict |
|------|----------------|----------------|---------|
| Low-confidence transactional selection | targeted refund question | CLARIFY; inspector matches; no task | PASS |
| High-confidence `needs_clarification=true` | targeted refund/rules question | CLARIFY; inspector matches; no task | PASS |
| Blank question | existing generic airline menu only | CLARIFY; inspector matches; no task | PASS |
| Idempotent replay | two identical assistant questions | event rows stay `3`; no task; same inspector question | PASS |

Screenshots:

- `screenshots/01-low-confidence-targeted.png`
- `screenshots/02-explicit-targeted.png`
- `screenshots/03-blank-fallback-menu.png`
- `screenshots/04-idempotent-replay.png`

All four screenshots were read back and are PNG `3164x2060`. The browser's
direct screenshot API initially returned blank canvases; those files were not
accepted. After navigating Codex to this task and showing the Browser panel,
the screenshots were recaptured through the already-authorized macOS window
capture and visually inspected.

The Browser harness only selects deterministic classifier results and pins the
fourth case's idempotency key. It does not replace the server proof: public API,
MySQL event storage, idempotent command replay, and zero mutation are separately
covered by automated Contract/Integration tests.
