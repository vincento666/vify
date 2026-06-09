# 042.3 Browser UAT

Date: 2026-06-09

Target: http://127.0.0.1:8047

Database: isolated SQLite database at
`artifacts/slices/042-runtime-policy-release-governance/042.3/uat.db`

## Real API Path

Evidence: `uat-api.txt`

- Created a profile without gates and confirmed `activate` returned 400.
- Created an active baseline profile and a draft candidate profile.
- Created a runtime-lab decision log for replay evidence.
- Ran validation, golden-matrix replay, and decision-log replay for the
  candidate profile.
- Approved the candidate profile.
- Set canary percent to 25.
- Activated the candidate profile.
- Queried release list and both profile statuses.

Result:

- blocked activation returned 400 with a validation gate message;
- validation, replay, approve, canary, and activate APIs returned 200;
- canary state persisted `canaryPercent = 25`;
- release activation recorded the previous active profile id;
- candidate profile became `active`;
- baseline profile became `archived`;
- release list returned the activated release.

## Browser Check

Screenshot:
`screenshots/browser-swagger-release.png`

The in-app browser loaded Swagger UI at
`http://127.0.0.1:8047/docs#/default/activate_profile_api_v1_runtime_policy_profiles__profile_id__activate_post`.

DOM check confirmed:

- `/api/v1/runtime-policy/profiles/{profile_id}/approve` visible;
- `/api/v1/runtime-policy/profiles/{profile_id}/canary` visible;
- `/api/v1/runtime-policy/profiles/{profile_id}/activate` visible;
- `/api/v1/runtime-policy/releases` visible;
- runtime-policy route group visible.

Verdict: PASS.
