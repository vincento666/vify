# Spec 013: Evaluation Loop Replica

## Goal

Add a product-level Evaluation module inspired by Coze Loop. The module lets Hify teams prove whether an Agent change improves quality before release, using repeatable datasets, evaluators, experiments, run records, and a result report.

The first MVP is a thin end-to-end loop: create cases, create a simple evaluator, run one Agent experiment, inspect failed cases. Workflow, Chatflow, LLM judge, import/export, and comparison analysis stay inside this spec as later slices, but they must not block the first usable MVP.

This is a product replica, not only a technical API replica. The spec must answer who uses it, how they use it, what business result it creates, what the user flow is, and whether the UI follows task-first information architecture, progressive disclosure, and an object-action-feedback model.

## Product Boundary

- Add one top-level sidebar entry: `Evaluation` / `评测`.
- Keep all core sub-functions inside the Evaluation module as tabs, not separate sidebar entries.
- Tab order: Experiments, Eval Sets, Evaluators, Run Records, Compare Analysis.
- The default tab is Experiments because the primary user task is to validate a target change, not to manage schemas.
- Eval Sets, Evaluators, Run Records, and Compare Analysis are supporting objects surfaced progressively from the experiment workflow.
- MVP tabs must exist, but the Compare Analysis tab may show a disabled or empty state until compare slices are implemented.
- Coze Loop is used as a local product reference for flow, information density, UI states, and feedback behavior.
- Coze Loop screenshots are reference artifacts only. Hify must not clone Coze branding, private assets, or pixel-perfect visual identity.
- The Hify implementation keeps the existing `/api/v1/...` envelope `{code, message, data}`.
- Hify uses the existing Python 3.12 + FastAPI + SQLAlchemy 2.0 architecture, not Coze Loop's Go microservice stack.
- Prompt-only evaluation is out of scope until Hify has a first-class Prompt module. In the MVP, prompt behavior is evaluated through Agent targets only.
- Production trace-to-eval automation is out of scope for the baseline, but the data model must leave a clear path for promoting chat or trace records into eval cases.

## MVP Cut

### MVP Includes

- One Evaluation sidebar entry with tabs.
- Manual Eval Set and Eval Case CRUD.
- Deterministic evaluator CRUD with exact-match and contains-keywords scoring.
- Agent-only experiment target.
- Synchronous local run execution with persisted Run and Case Result records.
- Result report with aggregate score, pass rate, failed cases, target output, score, and evaluator reason.
- Simple Run Records tab that lists runs and opens their reports.
- Compare Analysis tab shell with a clear empty or unavailable state.

### MVP Excludes

- Workflow and Chatflow target adapters.
- LLM judge evaluators.
- CSV import and export.
- User-visible version snapshot management; runs may copy case and evaluator configuration internally.
- Selected-case rerun.
- Cross-run comparison calculations.
- Queue workers, distributed execution, observability ingestion, and trace-to-eval automation.

## Users

- Agent author: wants to know whether a prompt, model, knowledge, or tool change improved Agent behavior.
- QA or evaluation owner: curates regression cases, scoring rules, and release gates.
- Product or operations owner: checks quality trends, failure clusters, and whether a release is safe.
- Developer: debugs failed cases and connects results back to Agent, chat, knowledge, and MCP behavior.

## Business Outcomes

- Replace subjective "it feels better" checks with repeatable quality scores.
- Prevent regressions before publishing Agent changes.
- Turn failed conversations and known bad cases into reusable regression cases.
- Give release owners a compact answer: ship, block, or investigate.

## Product Principles

### Task-first Information Architecture

- The first visible task is "run or inspect an experiment".
- Resource management appears as tabs and secondary actions, not as separate top-level navigation.
- The experiment create flow is progressive and follows the Coze Loop product rhythm adapted to Hify: basic info, eval set, Agent target, evaluator, review/run.

### Progressive Disclosure

- List views show status, score, pass rate, target, last run time, and primary actions only.
- Field mappings, evaluator prompts, concurrency, raw payloads, and advanced filters live in drawers, dialogs, or detail panels.
- Technical JSON is available for debugging but never the default product surface.

### Object-Action-Feedback Model

- Objects: Experiment, Eval Set, Eval Case, Evaluator, Run, Case Result, Comparison.
- MVP actions: create, edit, run, inspect failure.
- Later actions: import, stop, rerun, compare, export, promote to eval case.
- Feedback: run status, progress, score, pass rate, failed-case count, evaluator reason, output diff, and linked target context.

## Primary User Flow

1. User opens Evaluation and lands on Experiments.
2. User clicks create experiment.
3. User enters basic experiment info.
4. User selects an Eval Set.
5. User selects one Agent target.
6. User selects one or more Evaluators.
7. User reviews a compact run summary and starts the run.
8. Hify creates a Run Record and shows progress.
9. User opens the result report.
10. User filters failed cases, inspects input, output, expected answer, score, and evaluator reason.
11. User decides whether the Agent change can ship or needs investigation.

## Coze Loop Product Discovery Gate

Before implementing interactive UI slices, run a local Coze Loop reference session and save evidence:

- Deploy local Coze Loop using Docker Compose where feasible.
- Open the app in a real browser.
- Capture screenshots for login, Evaluation entry, Eval Set creation/import, Evaluator creation, Experiment creation, Run/Report, failed-case drilldown, and empty/error states.
- Save artifacts under `artifacts/slices/013-evaluation-loop-replica/discovery/`.
- Create `product-reverse.md` that records user, task, object, action, feedback, page states, and Hify adaptation decisions.
- Create a visual baseline note that distinguishes reusable UX patterns from Coze-specific branding.

If Coze Loop cannot be deployed locally, the discovery gate may use official docs and public screenshots, but the blocker and fallback must be recorded in the same artifact directory.

## Tabs

### Experiments

Default tab. Shows experiment list, create action, run status, score, pass rate, target, evaluators, and latest run. Detail view contains configuration, runs, report summary, and failed-case drilldown.

### Eval Sets

Manages reusable evaluation cases. MVP supports manual creation and case editing. CSV import, simple column mapping, version snapshots, and promotion from chat or trace records are later slices.

### Evaluators

Manages scoring rules. MVP supports deterministic exact-match and contains-keywords evaluators. LLM judge evaluators are a later slice. The UI shows evaluator purpose and status first; prompts, field mappings, and raw configuration are advanced details.

### Run Records

Shows historical runs across experiments. MVP is optimized for opening reports and failure investigation. Rerun and export are later slices.

### Compare Analysis

MVP shows a clear empty or unavailable state. Later slices compare two runs or target versions by score, pass rate, changed failures, improved cases, regressed cases, latency, and evaluator-specific metrics.

## MVP Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 013.0 Product discovery baseline | Local Coze Loop reference flow is captured and translated into Hify product decisions | Docs: product-reverse.md and screenshots; Browser UAT: reference paths recorded; no source implementation |
| 013.1 Evaluation workbench shell | Sidebar has one Evaluation entry and internal tabs: Experiments, Eval Sets, Evaluators, Run Records, Compare Analysis; Compare Analysis may be unavailable | RED: route/tab test fails; Unit: tab config helpers; E2E: navigation; UAT: tabs visible |
| 013.2 Eval Sets MVP | Users can create, list, edit, and delete eval cases without seeing raw schema first | RED: eval set API/UI test fails; Unit: case validation; Integration: CRUD; E2E: create/edit case; UAT: eval set usable |
| 013.3 Evaluators MVP | Users can create exact-match and contains-keywords evaluators, test them on sample input, and see readable score feedback | RED: evaluator API/UI test fails; Unit: deterministic scoring; Integration: CRUD/test; E2E: create/test evaluator; UAT: feedback visible |
| 013.4 Agent experiments and runs MVP | Users can create an Agent experiment, run it on an eval set, and produce case results synchronously | RED: experiment run test fails; Unit: Agent target mapping and aggregation; Integration: run persistence; E2E: create/run; UAT: progress/result visible |
| 013.5 Result report and run records MVP | Users can inspect run summary, failed cases, evaluator reasons, and target output from the report or Run Records tab | RED: report drilldown test fails; Unit: filtering shape; Integration: report endpoints; E2E: inspect failure; UAT: failure diagnosis works |

## Later Slices In This Spec

| Slice | Behavior | Notes |
|------|----------|-------|
| 013.6 CSV import and run export | Import eval cases from CSV and export run results | Adds file handling and column mapping after core loop is stable |
| 013.7 LLM judge evaluators | Add model-backed evaluators with criteria, threshold, score, and reason | Depends on provider/model reliability and cost controls |
| 013.8 Workflow and Chatflow targets | Add target adapters for Workflow and Chatflow | Reuses the same Experiment and Run model; adapters call the 011/012 run contracts and deep-link to the full-page canvas rather than embedding or cloning canvas UI |
| 013.9 Selected-case rerun | Rerun selected failed cases | Requires careful status and report update behavior |
| 013.10 Compare analysis | Compare two runs or target versions and identify regressions and improvements | Uses run data after enough experiments exist |

## Stop Conditions

- No separate top-level sidebar entries for Eval Sets, Evaluators, Run Records, or Compare Analysis.
- No raw schema-first UI.
- No Coze Loop brand, asset, or pixel-perfect clone.
- No first-class Prompt evaluation until a Prompt module exists.
- No Workflow, Chatflow, LLM judge, import/export, rerun, or comparison work in the MVP slices.
- No production-grade queue, distributed workers, or observability pipeline unless a later spec or later 013 slice adds them.
- No automatic trace-to-eval ingestion in the MVP.

## Workflow/Chatflow Target Adapter UI Boundary

The 2026-06-01 Coze canvas live audit affects 013 only at the target-link boundary:

- Evaluation target selection may list Workflow and Chatflow targets after 013.8, but it must not clone the canvas inside Evaluation.
- Target rows should show resource type, name, latest run status if available, and a link that opens the 011/012 full-page canvas route.
- Workflow cases map eval input to START/input variables.
- Chatflow cases map eval input to `USER_INPUT` or `sys.query` plus conversation profile variables from 012.
- Result reports link back to the target canvas/run evidence when debugging is needed.

## Evaluation Navigation Depth

Hify uses the global left sidebar for module navigation and the Evaluation
top-level tabs for Evaluation object navigation. This corresponds to Coze
Loop's Evaluation entry plus its nested Evaluation pages, but Hify renders the
nested Evaluation pages as tabs because this project does not have a dedicated
secondary left menu inside modules.

Run status, case status, date range, search, and similar controls are filters,
not another navigation level. They should use labeled filter fields, selects,
or explicit filter controls rather than segmented tab-like controls.

## Evidence

- Coze Loop public reference: Evaluation is organized around eval sets, evaluators, and experiments.
- Coze Loop local discovery evidence: `artifacts/slices/013-evaluation-loop-replica/discovery/`.
- Local Coze Loop browser UI/UX evidence is available as of `local-deploy-success-2026-06-02.md`.
- Local Coze Loop browser UI/UX was revalidated on 2026-06-08 with the Docker
  stack healthy at `http://localhost:8082`; DOM summaries are saved under
  `artifacts/slices/013-evaluation-loop-replica/discovery/coze-loop-live-2026-06-08/`.
- Screenshot baseline: `artifacts/slices/013-evaluation-loop-replica/discovery/screenshots/coze-loop-local-2026-06-02/`.
- Local browser coverage includes login/register, Evaluation navigation, Eval Set list/create/detail, Evaluator list and Code/LLM create pages, Experiment list/create/confirm/detail, metrics empty state, and validation feedback.
- A fully scored Coze failed-case drilldown was not captured because the local reference model and first-class evaluation target were not configured; Hify failed-case report requirements remain derived from the local experiment detail surface plus source-level Coze detail components and the 2026-06-08 local list/create DOM review.
- Hify target-evidence Browser UAT for Workflow target reports passed on 2026-06-08:
  `artifacts/slices/023-integration-architecture-deepening/023.7/uat.md`.
- Hify live LLM judge opt-in verification passed with OpenRouter
  `deepseek/deepseek-v4-flash`; the API key is not stored in repo artifacts.
- Workflow/Chatflow canvas live audit used for adapter boundary: `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`.
- Slice evidence: `artifacts/slices/013-evaluation-loop-replica/{slice-id}/`.
- Final high-spec gate evidence: `artifacts/slices/013-evaluation-loop-replica/final-gate/uat.md`.
- Hify browser UAT screenshots: `artifacts/slices/013-evaluation-loop-replica/final-gate/screenshots/browser-uat-experiments.png`, `browser-uat-run-report.png`, and `browser-uat-compare-analysis.png`.
