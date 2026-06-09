# 042.4 Browser UAT

Date: 2026-06-09

Target: http://127.0.0.1:8048

Database: isolated SQLite database at
`artifacts/slices/042-runtime-policy-release-governance/042.4/uat.db`

## Real API Path

Evidence: `uat-api.txt`

- Created an active baseline profile and a draft candidate profile.
- Created a runtime-lab decision log for replay evidence.
- Ran validation, golden-matrix replay, and decision-log replay for the
  candidate profile.
- Approved and activated the candidate profile.
- Rolled back the release.
- Queried release detail, evaluation-run detail, and both profile statuses.

Result:

- rollback returned 200 and release status `rolled_back`;
- baseline profile was restored to `active`;
- candidate profile became `archived`;
- release detail exposed audit events:
  `release_approved`, `release_activated`, `release_rolled_back`;
- evaluation detail exposed audit event `profile_validated`.

## Browser Check

Screenshot:
`screenshots/browser-swagger-rollback.png`

Playwright opened Swagger UI at
`http://127.0.0.1:8048/docs#/default/rollback_release_api_v1_runtime_policy_releases__release_id__rollback_post`.

DOM check confirmed:

- page title `Hify - Swagger UI`;
- `/api/v1/runtime-policy/releases` visible;
- `/api/v1/runtime-policy/releases/{release_id}/rollback` visible.

Screenshot file check confirmed a non-empty PNG at 1280 x 14429.

Verdict: PASS.
