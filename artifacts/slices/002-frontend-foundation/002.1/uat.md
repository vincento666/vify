# UAT 002.1: Frontend dependency hygiene

Status: PASS

Browser check:

- URL: `http://127.0.0.1:5173/`
- Server: `npm run preview -- --host 127.0.0.1 --port 5173`
- Screenshot: `screenshots/frontend-root.png`

Expected user-visible result:

- Frontend root opens without a blank screen.
- Build artifacts and installed dependencies remain ignored.

Evidence:

- RED: `red.txt` fails before `frontend/package.json` exists.
- Install: `npm-ci.txt` passes with `npm ci`.
- Integration: `build.txt` passes `npm run build`.
- E2E: `e2e.txt` confirms the preview server returns the app shell.
- Browser UAT: `browser-uat.txt` captures the app root through Chromium.
- Hygiene: `git status --ignored --short frontend/node_modules frontend/dist` marks both as ignored.
