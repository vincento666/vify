# 042.2 Browser UAT

Date: 2026-06-09

Target: http://127.0.0.1:8046

Database: isolated SQLite database at
`artifacts/slices/042-runtime-policy-release-governance/042.2/uat.db`

## Real API Path

Evidence: `uat-api.txt`

- Created an active global runtime policy profile.
- Posted `POST /api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix`.
- Created a runtime-lab session and posted a message to persist a decision log.
- Posted `POST /api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs`
  with `sessionId` and `action` filters.
- Listed persisted golden-matrix and decision-log replay evaluation runs.

Result:

- all HTTP statuses were 200;
- golden replay passed 4 cases with 0 failed cases;
- runtime message produced `AGENT_FALLBACK`;
- decision-log replay selected 1 log with 0 changed decisions;
- replay risk deltas had no unsupported actions;
- evaluation-run list APIs returned both persisted replay runs.

## Browser Check

Screenshot:
`screenshots/browser-swagger-replay.png`

The in-app browser loaded Swagger UI at
`http://127.0.0.1:8046/docs#/default/replay_golden_matrix_api_v1_runtime_policy_profiles__profile_id__replay_golden_matrix_post`.

DOM check confirmed:

- `/api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix` visible;
- `/api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs` visible;
- `/api/v1/runtime-policy/evaluation-runs` visible;
- runtime-policy route group visible.

Verdict: PASS.
