# UAT 001.3: Error envelope

Status: PASS

Browser check:

- URL: `http://127.0.0.1:8010/api/v1/not-found`
- Browser command: `npx playwright screenshot --browser chromium --full-page --viewport-size=1280,720`
- Screenshot: `screenshots/error-envelope.png`

Expected user-visible result:

```json
{"code":404,"message":"Not Found","data":null}
```

Evidence:

- RED: `red.txt` fails before `app.core.errors` exists.
- Unit: `unit.txt` passes `BizError` model checks.
- Contract/Integration: `contract.txt` and `integration.txt` pass envelope handling.
- E2E: `e2e.txt` passes against a running `uvicorn` server.
- Browser UAT: `browser-uat.txt` captures the error JSON through Chromium.
