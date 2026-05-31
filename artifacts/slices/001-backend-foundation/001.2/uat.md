# UAT 001.2: FastAPI health envelope

Status: PASS

Browser check:

- URL: `http://127.0.0.1:8010/api/v1/health`
- Browser command: `npx playwright screenshot --browser chromium --full-page --viewport-size=1280,720`
- Screenshot: `screenshots/health-response.png`

Expected user-visible result:

```json
{"code":200,"message":"success","data":{"status":"UP","components":{"app":"UP"}}}
```

Evidence:

- RED: `red.txt` fails with `404 != 200` before the route exists.
- Unit: `unit.txt` passes Python 3.12 and app import checks.
- Integration: `integration.txt` passes the FastAPI `TestClient` response contract.
- E2E: `e2e.txt` passes against a running `uvicorn` server.
- Browser UAT: `browser-uat.txt` captures the response through Chromium.
