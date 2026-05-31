# UAT 002.2: API client compatibility

Status: PASS

Browser checks:

- Success path: `http://127.0.0.1:5173/api/v1/health`
- Screenshot: `screenshots/proxy-health.png`
- Error path: `http://127.0.0.1:5173/provider`
- Screenshot: `screenshots/provider-error-toast.png`

Expected user-visible result:

- Frontend dev proxy returns the Python backend health envelope.
- Provider page remains rendered while the 404 API envelope is surfaced as a `Not Found` error toast.

Evidence:

- RED: `red.txt` fails before `test:unit` exists.
- Unit: `unit-final.txt` passes envelope unwrap and non-2xx Axios envelope extraction.
- Integration: `build.txt` passes `vue-tsc && vite build`.
- E2E: `e2e.txt` validates frontend proxy success and expected pre-003 provider 404.
- Browser UAT: `browser-health.txt` and `browser-provider.txt` capture success and error paths through Chromium.
