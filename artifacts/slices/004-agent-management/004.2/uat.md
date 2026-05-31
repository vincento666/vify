# UAT 004.2: Agent model validation

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5181/`
- Screenshot: `screenshots/invalid-model-rejected.png`

Expected user-visible result:

- Creating an Agent with a missing `modelConfigId` is rejected.
- Browser-visible response is `404 / Model config not found or disabled`.

Evidence:

- RED: `red.txt` fails because invalid/disabled model configs were accepted.
- Unit: `unit.txt` verifies validation happens before repository write.
- Integration: `integration.txt` verifies missing and disabled model configs are rejected.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` verifies the running API rejects an invalid model.
- Browser UAT: `browser-uat.txt` verifies rejection through the Vite proxy in Chromium.
