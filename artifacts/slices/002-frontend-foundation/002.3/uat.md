# UAT 002.3: One-command local startup

Status: PASS

Command:

```bash
HIFY_BACKEND_PORT=8011 HIFY_FRONTEND_PORT=5174 scripts/dev.sh
```

Browser check:

- URL: `http://127.0.0.1:5174/`
- Screenshot: `screenshots/dev-script-root.png`

Expected user-visible result:

- One command starts FastAPI and Vite.
- Frontend root opens.
- Frontend `/api/v1/health` proxy reaches the Python backend.
- Stop is verified by killing the test ports after UAT.

Evidence:

- RED: `red.txt` fails before `scripts/dev.sh` exists.
- Script help: `help.txt` verifies executable script entrypoint.
- Unit: `unit.txt` passes frontend request tests.
- Integration: `build.txt` passes frontend build.
- E2E: `e2e.txt` passes backend health, frontend proxied health, and frontend root checks.
- Browser UAT: `browser-uat.txt` captures the app root through Chromium.
