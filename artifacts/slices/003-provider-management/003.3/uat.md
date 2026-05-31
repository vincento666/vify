# UAT 003.3: Provider connection test

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5178/provider`
- Screenshot: `screenshots/connection-success.png`

Expected user-visible result:

- User clicks `测试` on a `mock://success` provider.
- UI shows success toast with latency and `2` discovered models.

Evidence:

- RED: `red.txt` fails before `ProviderConnectionTester` and route exist.
- Unit: `unit.txt` passes mock success/failure mapping.
- Integration: `integration.txt` passes `/test-connection` response shape.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` passes connection test against a running API.
- Browser UAT: `browser-uat.txt` clicks the button in Chromium and verifies the success toast.
