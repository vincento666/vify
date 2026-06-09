# 042.1 Browser UAT

Date: 2026-06-09

Target: http://127.0.0.1:8045

Database: isolated SQLite database at
`artifacts/slices/042-runtime-policy-release-governance/042.1/uat.db`

## Real API Path

Evidence: `uat-api.txt`

- Created a valid runtime policy profile through the API.
- Posted `POST /api/v1/runtime-policy/profiles/{profile_id}/validate`.
- Fetched the persisted evaluation run by id.
- Listed passed validation runs by `profileId`, `runType`, and `status`.
- Inserted a malformed profile directly into the isolated DB.
- Posted validation for the malformed profile through the API.
- Listed failed validation runs by `profileId`, `runType`, and `status`.

Result:

- all HTTP statuses were 200;
- valid profile validation returned `passed`;
- malformed profile validation returned `failed`;
- malformed failure reasons included threshold, classifier, and fallback response
  type violations;
- guardrail defaults were present on the validation run;
- evaluation-run list and detail APIs returned persisted records.

## Browser Check

Screenshot:
`screenshots/browser-swagger-validation.png`

The in-app browser loaded Swagger UI at
`http://127.0.0.1:8045/docs#/default/validate_profile_api_v1_runtime_policy_profiles__profile_id__validate_post`.

DOM check confirmed:

- `/api/v1/runtime-policy/profiles/{profile_id}/validate` visible;
- `/api/v1/runtime-policy/evaluation-runs` visible;
- `/api/v1/runtime-policy/evaluation-runs/{run_id}` visible;
- runtime-policy route group visible.

Verdict: PASS.
