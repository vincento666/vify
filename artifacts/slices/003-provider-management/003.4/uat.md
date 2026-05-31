# UAT 003.4: Provider health task

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5179/provider`
- Screenshot: `screenshots/health-badge.png`

Expected user-visible result:

- After `ProviderHealthChecker.check_once()`, provider row displays health badge `正常`.

Evidence:

- RED: `red.txt` fails before `ProviderHealthChecker` exists.
- Unit: `unit.txt` passes health checker update behavior.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` creates a provider, runs `check_once()`, and reads health via API.
- Browser UAT: `browser-uat.txt` confirms health badge in Chromium.
