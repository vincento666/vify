# Tasks 013: Evaluation Loop Replica

## 013.0 Product discovery baseline

- [x] Deploy or attempt to deploy local Coze Loop.
- [x] Capture browser screenshots for Evaluation entry, Eval Set, Evaluator, Experiment, Run Report, failed-case drilldown, and empty/error states.
- [x] Save artifacts under `artifacts/slices/013-evaluation-loop-replica/discovery/`.
- [x] Write `product-reverse.md` with users, tasks, objects, actions, feedback, page states, and Hify adaptation decisions.
- [x] Record fallback evidence if local Coze Loop cannot run.

## 013.1 Evaluation workbench shell

- [x] RED: Evaluation route/sidebar/tab test fails.
- [x] Add one sidebar entry for Evaluation / 评测.
- [x] Add `/evaluation` route and workbench shell.
- [x] Add internal tabs: Experiments, Eval Sets, Evaluators, Run Records, Compare Analysis.
- [x] Default to Experiments tab.
- [x] Show Compare Analysis as an explicit empty/unavailable state in MVP.
- [x] Gates pass.

## 013.2 Eval Sets

- [x] RED: Eval Set CRUD test fails.
- [x] Add eval set and eval case schema/repository/service/routes.
- [x] Add manual case creation and editing.
- [x] Keep CSV import and user-visible version snapshots out of MVP.
- [x] Build Eval Sets tab with non-schema-first copy and empty states.
- [x] Gates pass.

## 013.3 Evaluators

- [x] RED: Evaluator CRUD/test test fails.
- [x] Add evaluator schema/repository/service/routes.
- [x] Implement deterministic evaluators: exact match and contains keywords.
- [x] Keep regex, JSON field equals, and LLM judge out of MVP.
- [x] Add sample test action before saving or publishing evaluator changes.
- [x] Build Evaluators tab with feedback-first result display.
- [x] Gates pass.

## 013.4 Experiments and runs

- [x] RED: Experiment create/run test fails.
- [x] Add experiment, run, and case result schema/repository/service/routes.
- [x] Add Agent target adapter only.
- [x] Keep Workflow and Chatflow target adapters out of MVP.
- [x] Implement synchronous run execution over run-local copies of cases and evaluator config.
- [x] Persist run status, progress, aggregate score, pass rate, failed count, and timestamps.
- [x] Build Experiments tab create flow: target -> eval set -> evaluators -> review/run.
- [x] Gates pass.

## 013.5 Result report and run records

- [x] RED: Run report drilldown test fails.
- [x] Add run detail endpoint with summary, filters, failed cases, evaluator reasons, and target output.
- [x] Keep selected-case rerun and CSV export out of MVP.
- [x] Build report detail and Run Records tab.
- [x] Save Browser UAT screenshots for failure investigation flow.
- [x] Gates pass.

## Post-MVP backlog inside 013

- [x] 013.6 CSV import and run export.
- [x] 013.7 LLM judge evaluators.
- [x] 013.8 Workflow and Chatflow target adapters.
- [x] 013.9 Selected-case rerun.
- [x] 013.10 Compare analysis with score delta, pass-rate delta, newly failed cases, recovered cases, and unchanged failures.
