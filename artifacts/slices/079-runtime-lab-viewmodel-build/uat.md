# Browser UAT

- Command: `rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:5173/runtime-lab/chat HIFY_E2E_ARTIFACT_SLICE=079-runtime-lab-viewmodel-build node frontend/e2e/unified-routing-chat-lab-reset-session.mjs`
- Result: PASS
- Generated report: `artifacts/slices/034-unified-routing-chat-lab/079-runtime-lab-viewmodel-build/browser-reset-session.md`
- Scope: Runtime Lab page loads, creates a session, sends a turn, resets the session, clears transcript, and resets route action.
