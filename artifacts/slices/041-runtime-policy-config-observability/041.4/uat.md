# 041.4 Browser UAT

Date: 2026-06-09

Target: http://127.0.0.1:8044

Database: isolated SQLite database at
`artifacts/slices/041-runtime-policy-config-observability/041.4/uat.db`

## Real API Path

Evidence: `uat-api.txt`

- Created an active global runtime policy profile.
- Created a runtime-lab session.
- Posted a runtime-lab message with idempotency key `uat-decision-log`.
- Queried session decision logs.
- Queried filtered decision logs by session/profile/action/source/time.
- Queried an empty action filter.

Result:

- all HTTP statuses were 200;
- one decision log was persisted for the session;
- filtered query returned one matching log;
- empty action filter returned zero logs;
- `finalAction` matched runtime message route action;
- `policySnapshot.classifier.model` was `fake-runtime-classifier`;
- direct `apiKey` was absent from the persisted snapshot;
- route evidence included `routeDecision`.

## Browser Check

Screenshot:
`screenshots/browser-swagger-decision-log.png`

The in-app browser loaded Swagger UI at
`http://127.0.0.1:8044/docs#/default/list_decision_logs_api_v1_runtime_policy_decision_logs_get`.

DOM check confirmed:

- `/api/v1/runtime-policy/decision-logs` visible in OpenAPI UI;
- `/api/v1/runtime-policy/sessions/{session_id}/decision-logs` visible in OpenAPI UI;
- runtime-policy route group visible.

Verdict: PASS.
