# Spec 020: Coze-Grade Evaluation Replica

## Goal

Deepen the completed 013 Evaluation MVP into a Coze Loop-grade evaluation product. This spec focuses on the three product gaps confirmed by local Coze Loop browser UAT, Coze Loop source inspection, and the 013 final gate:

1. Eval Set versioning and column management.
2. Experiment stepper with field mapping and concurrency controls.
3. Evaluator Workbench v2 for LLM Judge debug and preset evaluator catalog.

013 remains the accepted MVP. 020 is the next high-granularity replica layer.

## Product Boundary

- Keep one Hify sidebar entry: `Evaluation` / `评测`.
- Keep sub-functions as tabs inside Evaluation, per the user's product direction.
- Do not clone Coze Loop branding, icons, or private assets.
- Copy Coze Loop's object lifecycle, task order, feedback states, and progressive disclosure.
- Do not expand into Prompt Engineering, Trace, or Tag Management in this spec. Those are follow-on modules after Evaluation's internal object lifecycle is Coze-grade.
- Do not add Code Evaluator execution in this spec unless sandboxing, timeouts, and dependency constraints are explicitly designed. Code Evaluator can be represented as a future shell or disabled option.

## Evidence Baseline

Local Coze Loop browser and source evidence:

- `artifacts/slices/013-evaluation-loop-replica/discovery/coze-module-audit-2026-06-02/audit.md`
- `artifacts/slices/013-evaluation-loop-replica/discovery/coze-module-audit-2026-06-02/screenshots/`
- Coze frontend routes: `artifacts/research/coze-loop-src/frontend/packages/loop-pages/evaluate-pages/src/app.tsx`
- Coze experiment steps: `artifacts/research/coze-loop-src/frontend/packages/loop-modules/evaluate/src/pages/experiment/create/constants/steps.tsx`
- Coze dataset detail composition: `artifacts/research/coze-loop-src/frontend/packages/loop-modules/evaluate/src/pages/dataset/detail/index.tsx`
- Coze evaluator list and create routes under `frontend/packages/loop-modules/evaluate/src/pages/evaluator/`

## Current Hify State

013 already provides:

- Eval Sets and Eval Cases.
- Deterministic Evaluators and thin LLM Judge.
- Agent, Workflow, and Chatflow experiment targets.
- Runs, reports, selected-case rerun, CSV import/export, and compare analysis.
- Browser UAT and E2E gates for the MVP loop.

020 does not re-prove that loop. It adds Coze-grade product depth around versioned data, versioned evaluators, and step-based experiment setup.

## Product Principles

### Task-First IA

- Default tab remains Experiments.
- Eval Sets and Evaluators remain supporting object tabs.
- Experiment creation becomes the primary task flow rather than a compact technical form.

### Progressive Disclosure

- Lists show status, version, counts, owners, and primary actions.
- Version records, column definitions, field mappings, evaluator debug payloads, and raw schemas live in detail pages, drawers, or later wizard steps.
- Debug/raw JSON is never the default first screen.

### Object-Action-Feedback

- Eval Set: edit draft -> submit version -> version tag appears -> associated experiments update.
- Evaluator: configure -> debug -> preview score/reason -> publish version.
- Experiment: choose dataset version -> map fields -> choose target/evaluators -> confirm -> run -> status/score/failure feedback.
- Case Result: inspect failure -> rerun/export/annotate later.

## Phase 1: Eval Set Versioning And Column Management

### Coze Reference

Local Coze Loop shows:

- Dataset list includes columns, item count, latest version, description, updater, creator, timestamps, and detail action.
- Dataset detail has `评测集` and `关联实验` tabs.
- Dataset detail shows a draft/version tag.
- Actions include `编辑列`, `添加数据`, `批量选择`, `版本记录`, and `提交新版本`.
- Rows have stable item IDs and typed fields such as `input` and `reference_output`.

Coze source confirms dataset detail is composed from `DatasetVersionTag`, `DatasetItemList`, and `DatasetRelatedExperiment`.

### Hify Gap

- Eval cases are fixed around `input` and `expectedOutput`.
- No user-visible draft/version lifecycle.
- No field schema or editable columns.
- No associated experiments tab on Eval Set detail.
- Runs can use current cases but do not bind a submitted Eval Set version.

### Target Behavior

- Eval Set detail becomes a product object page.
- Users can edit draft fields and rows.
- Users can submit a new version.
- Submitted versions are immutable and can be selected by experiments.
- Eval Set detail shows associated experiments using each version.
- Column management supports at least text fields and required/default indicators.

### Acceptance

- Users can create an eval set, add fields, add data, submit version `0.0.1`, edit draft again, and submit `0.0.2`.
- Experiments bind a specific eval set version.
- Browser UAT shows draft tag, version tag, version records, associated experiments, and disabled submit state when no draft changes exist.

## Phase 2: Experiment Stepper, Field Mapping, And Concurrency

### Coze Reference

Local Coze Loop shows experiment creation as a stepper:

1. Basic info.
2. Eval set.
3. Evaluation object, optional.
4. Evaluator, optional.
5. Confirm experiment config.

The basic step includes max concurrency. Source confirms `STEPS`, `StepIndicator`, `StepVisibleWrapper`, and `StepControls`, and includes target/evaluator field mapping fields.

### Hify Gap

- Experiment creation is a compact dialog.
- It uses current eval set ID and evaluator IDs, not version IDs.
- No dataset-to-target output mapping.
- No evaluator input field mapping.
- No confirmation step.
- No concurrency/retry controls.

### Target Behavior

- Replace the compact create dialog with a full-page or large-panel stepper.
- Step 1: name, description, concurrency, retry policy.
- Step 2: choose eval set version and inspect field schema/count.
- Step 3: choose Agent, Workflow, or Chatflow target and map eval case fields to target inputs.
- Step 4: choose evaluator versions and map dataset/target fields into evaluator inputs.
- Step 5: confirm all selections, mappings, and run settings, then launch.

### Acceptance

- Users can run the full stepper without seeing raw API schemas.
- Missing mapping produces human-readable validation feedback.
- Runs persist eval set version ID, evaluator version IDs, target mapping, evaluator mapping, concurrency, and retry settings.
- Browser UAT captures each step and the final confirm page.

## Phase 3: Evaluator Workbench V2

### Coze Reference

Local Coze Loop shows:

- Evaluator list has custom and preset tabs.
- New evaluator menu offers LLM Evaluator and Code Evaluator.
- LLM Evaluator creation has model selection, prompt editor, output contract with score and reason, debug, and create.
- Code Evaluator creation has template selection, language choice, code editor, sample `turn` data, trial run, and create.

Source confirms `evaluators/create/llm`, `evaluators/create/code`, `EvaluatorTemplateListPanel`, `DebugButton`, and prompt input schema generation.

### Hify Gap

- Current LLM Judge is a thin form config.
- No evaluator draft/version lifecycle.
- No preset evaluator catalog.
- No model/prompt/debug workbench.
- No Code Evaluator sandbox or disabled product shell.

### Target Behavior

- Add Evaluator Workbench page for LLM Judge.
- Users select model, write/edit prompt, define score/reason contract, provide sample input, run debug, and save/publish.
- Add preset evaluator tab with built-in Exact Match, Contains Keywords, and LLM Judge templates.
- Add evaluator versions so experiments bind stable evaluator versions.
- Add Code Evaluator as a clearly disabled or future option unless sandbox constraints are solved.

### Acceptance

- Users can debug LLM Judge before publishing.
- Debug result shows score, reason, pass/fail, and raw model response in an advanced drawer.
- Published evaluator versions are immutable and selectable in Experiment stepper.
- Browser UAT captures custom tab, preset tab, LLM workbench, debug result, and version publish.

## Stop Conditions

- No separate sidebar entries for Eval Set, Evaluator, Run Records, or Compare Analysis.
- No raw schema-first UI.
- No Code Evaluator execution without sandboxing, timeout, package, and resource controls.
- No Prompt Engineering, Trace, or Tag module implementation inside 020.
- No real-provider mandatory gate in default CI; live-provider gates must be opt-in.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 020.1 Eval Set draft/version model | Eval Sets have draft state, immutable versions, and version tags | RED: version contract fails; Unit: version builder; Integration: submit/list/get version; E2E: submit version; UAT: draft/version tags |
| 020.2 Eval Set column management | Users can manage typed fields and data rows in a Coze-like detail page | RED: field schema tests fail; Unit: column validation; Integration: row CRUD with schema; E2E: add/edit column and case; UAT: edit columns |
| 020.3 Eval Set related experiments | Eval Set detail shows associated experiments and version usage | RED: relation API test fails; Integration: experiment-version query; E2E: open related tab; UAT: associated experiments |
| 020.4 Experiment stepper shell | Compact dialog becomes stepper with basic/eval set/target/evaluator/confirm steps | RED: route/stepper test fails; Unit: step state; E2E: navigate steps; UAT: all steps visible |
| 020.5 Field mapping and run settings | Stepper persists target/evaluator mappings, concurrency, and retry settings | RED: mapping contract fails; Unit: mapping validation; Integration: run uses mappings; E2E: missing mapping feedback; UAT: confirm page |
| 020.6 Evaluator versions and preset catalog | Evaluators have immutable versions and preset catalog tab | RED: evaluator version tests fail; Integration: publish/list versions; E2E: preset tab; UAT: version selector |
| 020.7 LLM Evaluator workbench | LLM Judge workbench supports prompt, model, debug, score/reason preview, and publish | RED: debug contract fails; Unit: prompt adapter; Integration: debug endpoint; E2E: debug/publish; UAT: debug result |
| 020.8 Live-provider opt-in gate | Optional live-provider gate verifies real LLM Judge and experiment path when env vars exist | RED: skipped-without-env test fails first; Integration: live provider smoke; Docs: cost/risk note |

## Evidence

Each slice must save evidence under:

```text
artifacts/slices/020-coze-grade-evaluation-replica/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```
