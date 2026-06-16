# Tasks 020: Coze-Grade Evaluation Replica

## 020.1 Eval Set draft/version model

- [x] RED: Eval Set version contract tests fail.
- [x] Add additive version schema and repository.
- [x] Implement submit version and list versions.
- [x] Snapshot field schema and cases into immutable versions.
- [x] Add frontend version tag and submit-new-version action.
- [x] Add E2E: create draft, submit `0.0.1`, edit draft, submit `0.0.2`.
- [x] Save Browser UAT screenshots for draft, latest version, disabled submit state.
- [x] Gates pass.

## 020.2 Eval Set column management

- [x] RED: field schema validation tests fail.
- [x] Add eval set field schema API.
- [x] Implement typed text fields with required/display order.
- [x] Update case storage or metadata adapter to support dynamic fields.
- [x] Build edit-columns UI in Eval Set detail.
- [x] Add E2E: add `reference_output`-style field, edit case row, validate required field.
- [x] Save Browser UAT screenshots for edit columns and data table.
- [x] Gates pass.

## 020.3 Eval Set related experiments

- [x] RED: related experiment query test fails.
- [x] Add API to list experiments associated with an Eval Set/version.
- [x] Add `关联实验` tab to Eval Set detail.
- [x] Show experiment name, status, version, score, created/end time, and detail action.
- [x] Add E2E: create experiment using version and see it in related tab.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 020.4 Experiment stepper shell

- [x] RED: experiment create stepper route/UI test fails.
- [x] Replace compact create dialog with route or full-height stepper panel.
- [x] Add steps: Basic Info, Eval Set, Target, Evaluator, Confirm.
- [x] Add previous/next/skip behavior matching Coze semantics where applicable.
- [x] Keep Experiments tab as the default Evaluation entry.
- [x] Add E2E: navigate all steps and return.
- [x] Save Browser UAT screenshots for each step.
- [x] Gates pass.

## 020.5 Field mapping and run settings

- [x] RED: mapping persistence and validation tests fail.
- [x] Add target field mapping and evaluator field mapping schemas.
- [x] Add concurrency and retry settings to experiment creation.
- [x] Validate missing/ambiguous mappings with product-language errors.
- [x] Persist mappings and settings on experiment/run.
- [x] Update run execution to use mapped input/output fields.
- [x] Add E2E: run with mappings and inspect confirm page.
- [x] Save Browser UAT screenshots for mapping and confirm pages.
- [x] Gates pass.

## 020.6 Evaluator versions and preset catalog

- [x] RED: evaluator version and preset tests fail.
- [x] Add evaluator version schema and APIs.
- [x] Publish evaluator versions as immutable snapshots.
- [x] Add preset evaluator catalog tab.
- [x] Make Experiment stepper select evaluator versions.
- [x] Add E2E: publish evaluator version and select it in experiment.
- [x] Save Browser UAT screenshots for custom/preset/version selector.
- [x] Gates pass.

## 020.7 LLM Evaluator Workbench

- [x] RED: LLM evaluator debug endpoint test fails.
- [x] Build LLM evaluator workbench route/page.
- [x] Add model selection, prompt editor, sample input, score/reason output contract, and debug action.
- [x] Show debug result with score, reason, pass/fail, and raw output in advanced drawer.
- [x] Publish LLM evaluator version from workbench.
- [x] Add E2E: debug sample, publish version, select in experiment.
- [x] Save Browser UAT screenshots for debug and publish.
- [x] Gates pass.

## 020.8 Live-provider opt-in gate

- [x] RED: live-provider gate skip behavior test fails.
- [x] Add an opt-in integration test guarded by env vars.
- [x] Verify one real LLM Judge debug response does not use `mock judge`.
- [x] Verify one experiment run can use a real provider output when configured.
- [x] Record cost/risk note in evidence.
- [x] Save evidence under `artifacts/slices/020-coze-grade-evaluation-replica/020.8/`.
- [x] Gates pass.
