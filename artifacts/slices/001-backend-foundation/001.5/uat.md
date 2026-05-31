# UAT 001.5: Runtime services

Status: PASS

Browser checks:

- URL: `http://127.0.0.1:8010/readyz`
- Screenshot: `screenshots/readyz.png`
- URL: `http://127.0.0.1:8010/metrics`
- Screenshot: `screenshots/metrics.png`

Expected user-visible result:

- `/readyz` displays JSON with app `UP`, database `CONFIGURED`, Redis `NOT_CONFIGURED`.
- `/metrics` displays Prometheus text containing `hify_app_info`.

Evidence:

- RED: `red.txt` fails before `Settings`, `/readyz`, and `/metrics` exist.
- Unit: `unit.txt` passes settings defaults.
- Integration: `runtime-test.txt` passes readiness and metrics contracts.
- E2E: `e2e.txt` passes against a running `uvicorn` server.
- Browser UAT: `browser-readyz.txt` and `browser-metrics.txt` capture both endpoints through Chromium.
