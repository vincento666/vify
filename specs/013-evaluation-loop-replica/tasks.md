# Tasks 013: Evaluation Loop Replica

## 013.0 Product discovery baseline

- [x] Attempt to deploy local Coze Loop and record the blocker.
- [x] Retry local Coze Loop deployment on 2026-06-02 and record Docker layer blocker.
- [x] Successfully deploy local Coze Loop to a browser-accessible URL.
- [x] Capture browser screenshots for Evaluation entry, Eval Set, Evaluator, Experiment, experiment detail/report shell, metrics empty state, validation feedback, and empty/error states from the locally deployed Coze Loop frontend.
- [x] Save artifacts under `artifacts/slices/013-evaluation-loop-replica/discovery/`.
- [x] Write provisional `product-reverse.md` with users, tasks, objects, actions, feedback, page states, and Hify adaptation decisions based on official docs and source inspection.
- [x] Update provisional product reverse notes with Coze Loop source-confirmed experiment creation order: basic info -> eval set -> evaluation object -> evaluator -> confirm.
- [x] Record fallback evidence if local Coze Loop cannot run.
- [x] Replace or supplement fallback evidence with local browser UAT evidence before using Coze Loop for product-level UI/UX replication.
- [ ] Capture a fully scored Coze failed-case drilldown after a local model and first-class evaluation target are configured.

## 013.1 Evaluation workbench shell

- [x] RED: Evaluation route/sidebar/tab test fails.
- [x] Add one sidebar entry for Evaluation / 评测.
- [x] Add `/evaluation` route and workbench shell.
- [x] Add internal tabs: Experiments, Eval Sets, Evaluators, Run Records, Compare Analysis.
- [x] Default to Experiments tab.
- [x] Show Compare Analysis as an explicit empty state before compare data exists; later 013.10 enables the action.
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
- [x] Build Experiments tab create flow: basic info -> eval set -> Agent target -> evaluators -> review/run.
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
- [x] Verify 013.8 target adapters expose Workflow/Chatflow type labels and deep links to the 011/012 full-page canvas/run evidence instead of embedding canvas UI inside Evaluation.
- [x] 013.9 Selected-case rerun.
- [x] 013.10 Compare analysis with score delta, pass-rate delta, newly failed cases, recovered cases, and unchanged failures.

## Final Gate 2026-06-02

- [x] Backend evaluation integration suite green.
- [x] Backend contract suite green.
- [x] Frontend unit suite green after correcting the Vitest command.
- [x] Frontend production build green.
- [x] E2E green for shell, eval sets, evaluators, LLM judge, Agent experiment, Workflow/Chatflow targets, run records report, selected-case rerun, compare analysis, and CSV import/export.
- [x] Browser UAT screenshots saved under `artifacts/slices/013-evaluation-loop-replica/final-gate/screenshots/`.
- [x] Final UAT summary saved at `artifacts/slices/013-evaluation-loop-replica/final-gate/uat.md`.

## Target Adapter Recheck 2026-06-08

- [x] Local Coze Loop Docker stack revalidated as healthy and browser-accessible at `http://localhost:8082`.
- [x] Coze Loop Evaluation list/create surfaces re-reviewed from local browser DOM evidence.
- [x] Hify Workflow target failed-case report exposes target type, status, run id, target output, evaluator reason, and Workflow canvas debug deep link.
- [x] Browser UAT opened the target debug deep link and verified the Workflow run evidence page.
- [x] Hify live LLM judge opt-in test passed with OpenRouter model `deepseek/deepseek-v4-flash`.
- [ ] Coze Loop fully scored failed-case drilldown remains pending until the local Coze model config and first-class evaluation target are configured.
