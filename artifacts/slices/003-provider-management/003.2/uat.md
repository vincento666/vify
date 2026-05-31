# UAT 003.2: Model config contract

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5177/provider`
- Screenshots:
  - `screenshots/model-count.png`
  - `screenshots/model-popover.png`

Expected user-visible result:

- Provider table shows `1 个` for a provider with one enabled model.
- Clicking the model count shows `GPT-4o` / `gpt-4o`.

Evidence:

- RED: `red.txt` fails before `ProviderModelFacade` exists.
- Unit: `unit.txt` passes enabled/disabled model lookup behavior.
- Integration: `integration.txt` passes provider detail model response contract.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` seeds a model and reads it back through the running API.
- Browser UAT: `browser-uat.txt` confirms model count and popover in Chromium.
