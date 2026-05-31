# 013.7 Browser UAT: LLM Judge Evaluators

Date: 2026-06-01

## Scope

- Create an LLM Judge evaluator from the Evaluation workbench.
- Select a seeded mock provider model.
- Enter a rubric and run the sample test before saving.
- Verify the saved evaluator card preserves type, model binding, and rubric.

## Evidence

- Screenshot: `llm-judge.png`
- E2E log: `e2e.txt`
- Backend suite: `backend-evaluation-suite.txt`
- Frontend unit suite: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`

## Result

PASS. The UI exposes the LLM Judge evaluator path, requires a model binding, returns a structured judge result from the provider-backed evaluator, and persists the evaluator config.
