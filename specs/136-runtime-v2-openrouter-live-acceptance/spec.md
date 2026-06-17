# 136 Runtime V2 OpenRouter Live Acceptance

## Goal

Add an opt-in live acceptance gate proving Workflow runtime v2 can execute a real OpenRouter-backed LLM node through `/api/v1/workflows/{id}/runs-v2` and persist node-level debug/usage evidence.

## Scope

- Seed a live provider/model/agent from process environment only.
- Require a disposable `HIFY_DATABASE_URL` when the live gate is enabled.
- Create and publish a minimal Workflow with `START -> LLM -> END`.
- Run the Workflow through runtime v2.
- Assert the terminal output and LLM node output contain a live marker and do not contain `LLM mock:`.
- Assert LLM `__debug` and `__usage` are persisted on node outputs and echoed through `workflow_node_completed`.
- Record non-sensitive markdown evidence.

## Non-Goals

- Do not change runtime v2 production implementation.
- Do not persist provider credentials in repo files or default local database
  files.
- Do not add frontend behavior.

## Acceptance

- RED evidence records the missing runtime v2 live acceptance test.
- Default run skips safely without live opt-in.
- Ruff passes for the new acceptance test.
- Live OpenRouter DeepSeek V4 Flash runtime v2 gate passes with a disposable
  MySQL8 database.
- Secret scan finds no real provider key in tracked files, specs, or artifacts.
