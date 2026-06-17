# Plan 187: AI Assistant Tool Scheduler RWMutex

## Architecture

Add a small backend scheduling layer inside `app/modules/ai_assistant/domain/`
in the implementation slice. The planned target shape is:

```text
domain/
├── scheduler.py       # batching, RWMutex decisions, execution orchestration
├── resource_locks.py  # manifest template resolution and lock metadata
├── tools.py           # existing manifests and deterministic test handlers
└── harness.py         # integration point after 184 approval/sandbox checks
```

Persistence remains under `app/modules/ai_assistant/infra/` and must target
MySQL8. The implementation may extend `ai_assistant_tool_call` and event
payloads with scheduler metadata. If schema changes are required, add the
normal SQLAlchemy/alembic path already used by the project.

## Slice Order

### 187.0 Documentation Sign-Off

- create `spec.md`, `plan.md`, and `tasks.md`;
- record the 185/186 numbering collision;
- keep scope backend-first and Phase 4 only;
- save planning evidence under
  `artifacts/slices/187-ai-assistant-tool-scheduler-rwmutex/187.0/`.

### 187.1 Scheduler And RWMutex Backend Slice

Backend-only implementation.

Build:

- resource-key resolver for `read_resources` and `write_resources`;
- scheduler plan model with batch id, position, lock mode, resolved read keys,
  resolved write keys, and conservative fallback reason;
- RWMutex decision service that permits compatible read batches and serializes
  writes;
- deterministic execution path for multiple planned tool calls;
- metadata persistence on tool calls and scheduler/tool events;
- contract payload additions for run events/result/inspector where applicable.

Gates:

- RED unit tests for scheduler grouping and write serialization;
- RED integration test for MySQL8 metadata persistence;
- RED contract/E2E test for visible scheduler metadata;
- focused unit tests;
- MySQL8 integration tests;
- AI Assistant contract tests;
- backend E2E tests;
- lint/type gates used by the existing AI Assistant backend;
- SQLite scan/boundary evidence for new tests.

### 187.2 Aggregate Backend Acceptance

- rerun the 187.1 focused gates;
- rerun 184 AI Assistant backend regressions relevant to harness, security, and
  inspector contracts;
- confirm no frontend visual files changed;
- save final evidence and residual risks;
- update `tasks.md` statuses only after evidence files exist.

## TDD Evidence Discipline

The implementation slice must start with RED tests and save failing output
under:

```text
artifacts/slices/187-ai-assistant-tool-scheduler-rwmutex/187.1/red.txt
```

Recommended RED targets:

```text
rtk pytest tests/unit/ai_assistant/test_tool_scheduler.py -q
rtk pytest tests/integration/ai_assistant/test_scheduler_persistence.py -q
rtk pytest tests/contract/test_ai_assistant_scheduler_api.py -q
rtk pytest tests/e2e/test_ai_assistant_scheduler_e2e.py -q
```

Names may change during implementation, but evidence must preserve the same
behavioral coverage.

## Backend Gate Plan

Focused implementation gates:

```text
rtk pytest tests/unit/ai_assistant -q
rtk pytest tests/integration/ai_assistant -q
rtk pytest tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_security_api.py tests/contract/test_ai_assistant_inspector_api.py -q
rtk pytest tests/e2e/test_ai_assistant_kernel_e2e.py tests/e2e/test_ai_assistant_security_e2e.py -q
```

Add scheduler-specific contract/E2E paths once RED tests exist.

MySQL8-only confirmation must include either the existing MySQL8 boundary gate
or a focused scan proving the new scheduler tests do not introduce SQLite URLs.

## Frontend Gate Plan

No frontend visual work is planned. Do not edit:

```text
frontend/src/**/*.vue
frontend/src/**/*.css
frontend/src/** visual-size TS
```

Because this slice is backend-only, browser UAT and `remScaleClosure` are not
required unless an implementation later touches frontend-visible visuals. If
that happens, stop and split the frontend work into a separate spec or slice.

## Live LLM Gate Plan

No live LLM gate is required for 187. Default tests must stay deterministic.
Any optional future OpenRouter probe must:

- be skipped unless an explicit env flag is present;
- read credentials only from environment variables;
- save skipped/live evidence separately from required GREEN gates.

