# UAT 004.1: Agent CRUD

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5180/agent`
- Screenshots:
  - `screenshots/agent-created.png`
  - `screenshots/agent-updated.png`
  - `screenshots/agent-deleted.png`

Expected user-visible result:

- User can create an Agent with a model.
- User can edit Agent basic fields and save.
- User can delete the Agent.

Evidence:

- RED: `red.txt` fails before agent schemas/routes exist.
- Unit: `unit.txt` passes camelCase schema validation.
- Integration: `integration.txt` passes create/list/update/delete route contract.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` creates provider/model seed and creates an Agent against running API.
- Browser UAT: `browser-uat.txt` completes create/edit/delete in Chromium.
