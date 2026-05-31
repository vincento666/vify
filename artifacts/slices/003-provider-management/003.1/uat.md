# UAT 003.1: Provider CRUD

Status: PASS

Browser flow:

- URL: `http://127.0.0.1:5176/provider`
- Started with: `HIFY_DATABASE_URL=sqlite:///artifacts/slices/003-provider-management/003.1/uat.db HIFY_BACKEND_PORT=8012 HIFY_FRONTEND_PORT=5176 scripts/dev.sh`
- Screenshots:
  - `screenshots/provider-created.png`
  - `screenshots/provider-updated.png`
  - `screenshots/provider-deleted.png`

Expected user-visible result:

- User can create an OpenAI provider and see it in the table.
- User can edit the provider and see a success message.
- User can delete the provider and see a success message.

Evidence:

- RED: `red.txt` fails before provider module and routes exist.
- Unit: `unit.txt` passes frontend camelCase schema validation.
- Integration: `integration.txt` passes create/list/update/delete route contract.
- Quality: `ruff.txt` and `mypy.txt` pass.
- E2E: `e2e.txt` passes CRUD against a running `uvicorn` server.
- Browser UAT: `browser-uat.txt` completes create/edit/delete in Chromium.
