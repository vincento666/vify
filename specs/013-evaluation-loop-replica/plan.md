# Plan 013: Evaluation Loop Replica

## Architecture

- Add `app/modules/evaluation/` with the same local module shape as existing Hify modules:
  - `web/` for FastAPI routes and request/response schemas.
  - `domain/` for Eval Set, Evaluator, Experiment, Run, Result, scoring, aggregation, and target adapters.
  - `infra/` for SQLAlchemy repositories.
  - `api/` for cross-module facades when Agent, Workflow, Chatflow, or Chat needs to promote records into evaluation.
- Add frontend route `/evaluation` and a single sidebar item.
- Build an Evaluation workbench page with tabs, defaulting to Experiments.
- Keep API envelope compatibility with `{code, message, data}`.
- Keep target execution behind adapters:
  - MVP implements only the Agent target adapter, calling the existing chat/agent path with one eval case input.
  - Later Workflow target adapter calls the existing workflow run path and links report rows back to the 011 full-page canvas/run evidence.
  - Later Chatflow target adapter maps eval case input into conversation-shaped system variables and links report rows back to the 012 full-page canvas/run evidence.
- Keep first implementation synchronous or locally staged, but persist `Run` and `RunCaseResult` status so a later worker or queue can replace execution without changing product concepts.

## MVP Complexity Budget

- Ship one thin vertical path before broadening the object model.
- No queue, no background worker, no LLM judge, no CSV import/export, no compare engine, no selected-case rerun, no Workflow/Chatflow adapters.
- Keep all tabs visible for product IA, but allow post-MVP tabs or actions to show empty/unavailable states.
- Prefer copying case and evaluator configuration into each run over building user-visible version management in the MVP.

## Domain Model

- `EvalSet`: named collection of reusable eval cases.
- `EvalSetVersion`: later user-visible snapshot; MVP may store a run-local copy of case configuration.
- `EvalCase`: input, expected output, metadata, tags, and optional source reference.
- `Evaluator`: scoring object visible to users.
- `EvaluatorVersion`: later user-visible snapshot; MVP may store a run-local copy of evaluator configuration.
- `Experiment`: saved plan binding target, eval set version, evaluator versions, and run options.
- `ExperimentRun`: one execution attempt with status, progress, aggregate metrics, and timestamps.
- `RunCaseResult`: one target output plus evaluator scores and reasons for one eval case.
- `Comparison`: later derived view comparing two runs.

## MVP API Shape

- `GET /api/v1/evaluation/eval-sets`
- `POST /api/v1/evaluation/eval-sets`
- `GET /api/v1/evaluation/eval-sets/{id}`
- `PUT /api/v1/evaluation/eval-sets/{id}`
- `GET /api/v1/evaluation/evaluators`
- `POST /api/v1/evaluation/evaluators`
- `POST /api/v1/evaluation/evaluators/{id}/test`
- `GET /api/v1/evaluation/experiments`
- `POST /api/v1/evaluation/experiments`
- `POST /api/v1/evaluation/experiments/{id}/runs`
- `GET /api/v1/evaluation/runs`
- `GET /api/v1/evaluation/runs/{id}`

Exact endpoint names may be refined during implementation, but the product objects must remain stable.

## Later API Shape

- `POST /api/v1/evaluation/eval-sets/{id}/cases/import`
- `POST /api/v1/evaluation/eval-sets/{id}/versions`
- `POST /api/v1/evaluation/runs/{id}/rerun`
- `GET /api/v1/evaluation/runs/{id}/export`
- `GET /api/v1/evaluation/compare?leftRunId=...&rightRunId=...`

## Evaluator Types

- MVP deterministic baseline:
  - exact match.
  - contains all keywords.
- Later deterministic evaluators:
  - regex match.
  - JSON field equals.
- Later LLM judge:
  - score range.
  - pass threshold.
  - readable criteria.
  - evaluator reason.
- Later:
  - code evaluator.
  - human annotation.
  - production monitor evaluator.

## UI Shape

- Sidebar item: Evaluation / 评测.
- Internal tabs:
  - Experiments.
  - Eval Sets.
  - Evaluators.
  - Run Records.
  - Compare Analysis, shown as an empty/unavailable tab in the MVP.
- Experiments tab is default.
- Experiment list shows target, latest run status, score, pass rate, failed cases, updated time, and actions.
- Create experiment flow is task ordered:
  1. Select target.
  2. Select eval set.
  3. Select evaluators.
  4. Review and run.
- Detail view uses progressive disclosure:
  - summary first.
  - failed cases next.
  - advanced config and raw payload last.
- Eval Set and Evaluator tabs are management surfaces, but must keep task language: "cases", "criteria", "score", "reason", not raw storage schema.

## Product Discovery Work

Before implementation slices, run Coze Loop locally when feasible:

- Clone and start Coze Loop according to official quickstart.
- Use browser automation or manual browser UAT to capture the main evaluation paths.
- Save screenshots and notes under `artifacts/slices/013-evaluation-loop-replica/discovery/`.
- Write `product-reverse.md` with:
  - who uses each page.
  - the page's primary task.
  - objects and actions.
  - visible feedback.
  - progressive disclosure decisions.
  - what Hify will copy as product behavior.
  - what Hify will intentionally not copy.

## Testing Strategy

- Contract tests verify all Evaluation APIs return the existing envelope.
- Integration tests cover CRUD, experiment creation, run persistence, result aggregation, and report detail.
- Unit tests cover deterministic evaluator scoring, field validation, Agent target mapping, aggregation, and report filtering shape.
- E2E tests cover the primary product path: create eval set, create evaluator, create experiment, run, inspect failed case.
- Browser UAT must save screenshots for each slice that changes visible UI.

## ADR

### Decision

Implement Evaluation as one top-level module with internal tabs for Experiments, Eval Sets, Evaluators, Run Records, and Compare Analysis. Ship the first MVP as an Agent-only deterministic evaluation loop; keep broader target, judge, import/export, rerun, and comparison features as later slices inside the same spec.

### Drivers

- The user's main task is to validate target quality, not browse technical sub-systems.
- Hify should preserve a compact sidebar and avoid fragmenting related evaluation objects.
- Coze Loop's eval-set/evaluator/experiment model is a useful product reference, but Hify must adapt it to its own Agent, Workflow, and Chatflow boundaries.
- The first implementation must avoid building a full evaluation platform before one usable quality loop exists.

### Alternatives Considered

- Separate sidebar entries for Eval Sets, Evaluators, and Experiments.
- Hidden technical-only evaluation APIs with no product workbench.
- Pixel-perfect Coze Loop clone.
- Full Coze Loop-style evaluation platform in the first implementation batch.

### Why Chosen

Internal tabs preserve product cohesion and support task-first flow. The thin MVP proves the user value with less operational complexity, while the tab shell leaves room for the complete Coze Loop-inspired product shape.

### Consequences

- Evaluation page must handle several object types without becoming visually crowded.
- The Experiments tab needs strong defaults and empty states.
- Future trace and prompt features should plug into Evaluation without adding new top-level navigation.
- Compare Analysis may be visible before it is functional, so the empty state must be explicit and not misleading.

### Follow-ups

- Ship Compare Analysis after enough run data exists.
- Add trace-to-eval promotion after observability data is first-class.
- Add code and human evaluators after deterministic and LLM judge evaluators are stable.

## Slice Order

MVP: 013.0 -> 013.1 -> 013.2 -> 013.3 -> 013.4 -> 013.5

Later within this spec: 013.6 -> 013.7 -> 013.8 -> 013.9 -> 013.10
