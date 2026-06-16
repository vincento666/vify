# Plan 020: Coze-Grade Evaluation Replica

## Architecture Approach

020 extends the existing `app/modules/evaluation` module without replacing 013.

New backend concepts:

- `EvalSetFieldSchema`: user-managed field definitions for an Eval Set draft.
- `EvalSetVersion`: immutable snapshot of field schema and cases.
- `EvaluatorVersion`: immutable snapshot of evaluator config, prompt, model, and input schema.
- `ExperimentMapping`: target field mapping and evaluator field mapping stored on experiments/runs.
- `RunSettings`: concurrency, retry count, and execution options.

Frontend additions:

- Eval Set detail page with data tab, associated experiments tab, version records, and column management.
- Experiment create stepper replacing the compact dialog.
- Evaluator Workbench page for LLM Judge and preset evaluator catalog.

## Data Model Direction

Additive tables only:

- `eval_set_field`
  - eval_set_id
  - key
  - label
  - content_type
  - required
  - display_order
  - deleted
- `eval_set_version`
  - eval_set_id
  - version
  - schema_snapshot
  - case_snapshot
  - description
  - created_by placeholder
  - created_at
- `evaluator_version`
  - evaluator_id
  - version
  - evaluator_type
  - config_snapshot
  - input_schema
  - model_config_id nullable
  - prompt_snapshot nullable
  - created_at
- extend `evaluation_experiment`
  - eval_set_version_id
  - evaluator_version_ids
  - target_field_mapping
  - evaluator_field_mapping
  - item_concurrency
  - item_retry_count

Keep existing 013 fields for compatibility until migration is proven.

## API Direction

Eval Set:

- `GET /api/v1/eval-sets/{id}/fields`
- `PUT /api/v1/eval-sets/{id}/fields`
- `POST /api/v1/eval-sets/{id}/versions`
- `GET /api/v1/eval-sets/{id}/versions`
- `GET /api/v1/eval-sets/{id}/related-experiments`

Evaluator:

- `POST /api/v1/evaluators/{id}/versions`
- `GET /api/v1/evaluators/{id}/versions`
- `GET /api/v1/evaluators/presets`
- `POST /api/v1/evaluators/llm-debug`

Experiment:

- `POST /api/v1/evaluation-experiments` accepts version IDs, mappings, and run settings.
- Existing endpoint remains backward compatible for 013 tests until 020 migration completes.

## Frontend Product Shape

Eval Set detail:

- Header: name, description, latest version, draft state, updated time.
- Tabs: `评测集` and `关联实验`.
- Toolbar: edit columns, add data, batch select, version records, submit new version.
- Table: row ID, dynamic fields, created/updated time, edit/view.

Experiment stepper:

- Full-page route or full-height panel.
- Step indicator persists at top.
- Bottom controls include previous/next/skip where applicable and max concurrency.
- Confirm page is read-only and compact.

Evaluator Workbench:

- Evaluators tab separates custom and presets.
- LLM workbench uses product labels: model, criteria prompt, sample data, debug result, publish.
- Code evaluator is not executable until sandboxing exists.

## Testing Strategy

- RED tests first for every slice.
- Unit tests for version snapshot builders, field schema validation, mapping validation, evaluator debug adapter.
- Integration tests for new endpoints and backward compatibility with 013.
- E2E tests for each product flow.
- Browser UAT comparing Hify against local Coze Loop screenshots from the audit directory.
- Optional live-provider gate is skipped unless explicit env vars are present.

## Risks

- Version tables can duplicate large case snapshots. Start with small snapshot JSON and revisit storage when datasets grow.
- Field mapping can become schema-heavy. UI must use human labels and examples, with raw mapping hidden.
- LLM debug can cost money. Keep live-provider gate opt-in and mock provider as default.
- Code evaluator is high risk. Keep it out of executable scope until sandboxing is specified.

## Dependencies

- 013 final gate complete.
- Provider/model management from 003.
- Agent/Workflow/Chatflow target availability from 004/011/012.
- Optional live-provider gate depends on configured provider credentials.

## Done Criteria

020 is done when:

- Eval Set version lifecycle works and is visible.
- Experiment creation uses stepper with version IDs, field mappings, and run settings.
- LLM Evaluator Workbench can debug and publish versions.
- Existing 013 E2E remains green.
- Browser UAT evidence shows Hify matching the Coze object-action-feedback pattern at high granularity.
