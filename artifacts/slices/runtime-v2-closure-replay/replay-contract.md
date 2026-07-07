# Runtime V2 Closure Replay Contract

Status: open-loop contract, approved path A.

Date: 2026-07-07

Base branch/head:

```text
codex/runtime-v2-production-upgrade @ d6fc969c
```

Replay branch/worktree:

```text
codex/runtime-v2-closure-replay
/Users/vincento/work/develop/hify-runtime-v2-closure-replay
```

Source branch:

```text
codex/runtime-v2-specs-213-plus
final audit: b5271579 docs(runtime): record completion audit
closure: 460ea5e1 test(runtime): seal spec 221 exit regression and production upgrade closure
```

## Goal

Replay runtime-only 213-221 closure work onto current 222+ head without losing
AI Assistant MVP commits or 222 evidence.

## Include Scope

Allowed replay paths:

```text
alembic/versions/0025_workflow_node_run_selection_state.py
app/core/config.py
app/core/database.py
app/core/sanitization.py
app/core/schema.py
app/main.py
app/modules/runtime/
app/modules/workflow/
app/modules/runtime_lab/
app/modules/customer_assistant/
docs/chatflow-sop-state-boundary.md
docs/customer-assistant-runtime.md
docs/mysql8-weaviate-demo.md
docs/runtime/
docs/testing/acceptance-gates.md
frontend/e2e/api-resource-tool-builder.mjs
frontend/e2e/chatflow-running-path-animation.mjs
frontend/e2e/chatflow-runtime-timeline-ui.mjs
frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs
frontend/e2e/fixtures/sop-matrix/
frontend/e2e/runtime-lab-sop-v2-binding.mjs
frontend/e2e/runtime-ops-*.mjs
frontend/e2e/runtime-run-helpers.mjs
frontend/e2e/runtime-v2-*.mjs
frontend/e2e/sop-matrix-runtime-v2.mjs
frontend/e2e/unified-routing-chat-lab-scale.mjs
frontend/e2e/workflow-*.mjs
frontend/src/api/runtimeOps.ts
frontend/src/api/workflow.ts
frontend/src/api/workflowRuntimeV2.test.ts
frontend/src/appNavigation.ts
frontend/src/router/index.ts
frontend/src/router/runtime-ops-router.test.ts
frontend/src/views/runtimeOps/
frontend/src/views/workflow/
scripts/runtime_job_worker.py
specs/211-runtime-v2-chatflow-async-refs/stream-refs-matrix.md
specs/213-runtime-async-default-invocation-gateway/
specs/214-runtime-dag-multipath-semantics/
specs/215-runtime-dag-frontier-scheduler/
specs/216-chatflow-sop-compat-on-dag/
specs/217-runtime-v2-node-compatibility-matrix/
specs/218-runtime-production-job-scheduler/
specs/219-runtime-event-cancel-ratelimit-backpressure/
specs/220-runtime-observability-ops-module/
specs/221-runtime-capacity-fault-acceptance/
tests/contract/runtime/
tests/contract/runtime_dag/
tests/contract/runtime_gateway/
tests/contract/runtime_jobs/
tests/contract/runtime_lab/
tests/contract/test_chatflow_runtime_job_worker_gateway.py
tests/contract/workflow/
tests/acceptance/test_runtime_v2_live_openrouter_llm.py
tests/integration/chatflow/
tests/integration/customer_assistant/
tests/integration/mysql8/
tests/integration/runtime/
tests/integration/runtime_jobs/
tests/integration/runtime_lab/
tests/integration/workflow/
tests/unit/core/
tests/unit/runtime/
tests/unit/runtime_lab/
tests/unit/workflow/
artifacts/slices/034-unified-routing-chat-lab/214.5/
artifacts/slices/105-runtime-lab-sop-chatflow-v2-binding/214.5/
artifacts/slices/214-runtime-dag-multipath-semantics/
artifacts/slices/215-runtime-dag-frontier-scheduler/
artifacts/slices/221-runtime-capacity-fault-acceptance/
artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/
artifacts/slices/runtime-v2-production-upgrade/
```

## Protected Scope

Do not replay, delete, or downgrade these paths:

```text
app/modules/ai_assistant/
frontend/src/views/aiAssistant/
frontend/e2e/ai-assistant-*.mjs
specs/222-ai-assistant-general-harness-mvp/
tests/*ai_assistant*
tests/contract/test_ai_assistant_*.py
tests/e2e/test_ai_assistant_*.py
tests/eval/test_ai_assistant_*.py
tests/integration/ai_assistant/
tests/unit/ai_assistant/
tests/support/ai_assistant_memory_repo.py
```

## Method

Use path-limited replay from `codex/runtime-v2-specs-213-plus`.

Do not use wholesale merge.

If a source commit mixes protected and allowed paths, apply allowed paths only.

## Verification

Runtime focused gates:

```bash
rtk uv run pytest tests/unit/core tests/unit/runtime tests/unit/runtime_lab tests/unit/workflow -q
rtk uv run pytest tests/contract/runtime tests/contract/runtime_dag tests/contract/runtime_gateway tests/contract/runtime_jobs tests/contract/runtime_lab tests/contract/workflow -q
rtk uv run pytest tests/integration/runtime tests/integration/runtime_jobs tests/integration/runtime_lab tests/integration/workflow tests/integration/chatflow tests/integration/customer_assistant -q
rtk npm --prefix frontend run test:unit -- src/router/runtime-ops-router.test.ts src/views/runtimeOps
rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
```

222 regression smoke:

```bash
rtk test -f specs/222-ai-assistant-general-harness-mvp/spec.md
rtk test -f app/modules/ai_assistant/domain/harness.py
rtk uv run pytest tests/unit/ai_assistant/test_qwen_live_planner.py tests/contract/test_ai_assistant_kernel_api.py tests/contract/test_ai_assistant_security_api.py -q
rtk npm --prefix frontend run test:unit -- src/api/aiAssistant.test.ts src/views/aiAssistant/aiAssistantShell.test.ts
```

Diff guards:

```bash
rtk git diff --name-status d6fc969c..HEAD -- app/modules/ai_assistant frontend/src/views/aiAssistant specs/222-ai-assistant-general-harness-mvp tests/unit/ai_assistant tests/contract/test_ai_assistant_*.py tests/e2e/test_ai_assistant_*.py tests/eval/test_ai_assistant_*.py
rtk git diff --check
```

## Stop Rules

Stop if:

- any protected path is deleted or downgraded;
- 222 smoke fails due replay;
- runtime replay needs unapproved dependency, production secret, external service, release, or irreversible action;
- verifier failure repeats without a narrower hypothesis;
- path-limited replay cannot preserve 222 and runtime closure together.

## Replay Adjustments

Observed during current-head replay:

- Preserved 222 OpenRouter default model `qwen/qwen3.6-27b` while keeping
  runtime DB pool and runtime limit settings.
- Removed stale moved tests:
  `tests/unit/runtime_lab/test_sop_checkpoint_from_row_rebuild.py` and
  `tests/integration/workflow/test_runtime_job_repository.py`.
- Replayed missed runtime gateway files that still referenced retired
  `runs-v2` aliases.
- Made runtime ops audit test actor unique so reruns against a persistent local
  DB do not collide with prior audit rows.
