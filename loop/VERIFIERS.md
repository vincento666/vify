# Loop Verifiers: Spec 226 AI Assistant Runtime Convergence

合同已于 2026-07-18 获批。每个命令只在相应 RED 测试和 slice evidence 建立后执行。

## Contract And Worktree

    rtk git status --short --branch
    rtk git diff --check
    rtk rg -n "Status|Success Predicate|Goal Gate|Human Gates" specs/226-ai-assistant-runtime-convergence-shell
    rtk rg -n "Status|Decision|Options|Consequences|Guardrails" docs/adr/0005-ai-assistant-runtime-job-substrate.md

## 226.1 Agent Harness Customer Adapter

    rtk uv run pytest tests/contract/agent_harness/test_public_interface.py tests/unit/customer_assistant/test_react_worker.py -q --tb=short
    rtk uv run pytest tests/integration/customer_assistant -q --tb=short
    rtk uv run ruff check app/modules/agent_harness app/modules/customer_assistant

## 226.2 AI Assistant Adapter

    rtk uv run pytest tests/contract/agent_harness tests/unit/ai_assistant tests/unit/customer_assistant/test_react_worker.py -q --tb=short
    rtk uv run pytest tests/integration/ai_assistant tests/integration/customer_assistant -q --tb=short
    rtk uv run ruff check app/modules/agent_harness app/modules/ai_assistant app/modules/customer_assistant

## 226.3 Runtime Job Core

    rtk uv run pytest tests/unit/workflow/test_runtime_job_worker.py tests/contract/runtime_jobs tests/integration/runtime_jobs -q --tb=short
    rtk uv run pytest tests/contract/test_workflow_runtime_job_gateway.py tests/integration/runtime/test_debug_runs_default_async.py -q --tb=short
    rtk uv run alembic heads
    rtk uv run alembic check

## 226.4 Security

    rtk uv run pytest tests/unit/ai_assistant/test_permission_policy.py tests/contract/ai_assistant/test_trusted_principal.py tests/integration/ai_assistant/test_scope_authorization.py tests/integration/ai_assistant/test_approval_actor_audit.py -q --tb=short

## 226.5 Durable Worker And HA

    rtk uv run pytest tests/contract/ai_assistant/test_durable_job_gateway.py tests/integration/ai_assistant/test_standalone_worker_takeover.py tests/integration/ai_assistant/test_worker_lease_fencing.py tests/integration/ai_assistant/test_sse_short_sessions.py tests/e2e/test_ai_assistant_streaming_e2e.py -q --tb=short

## 226.6 Activity And Child Lifecycle

    rtk uv run pytest tests/unit/ai_assistant/test_activity_correlation.py tests/contract/ai_assistant/test_subagent_lifecycle.py tests/integration/ai_assistant/test_customer_subagent_adapter.py -q --tb=short
    rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/runActivityProjection.test.ts

## 226.7 Product Shell

    rtk npm --prefix frontend run test:unit -- src/views/aiAssistant
    rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts src/views/agentChatRemGovernance.test.ts
    rtk npm --prefix frontend run build
    rtk node frontend/e2e/ai-assistant-runtime-activity-shell.mjs

Browser UAT 必须写入
`artifacts/slices/226-ai-assistant-runtime-convergence-shell/226.7/`，使用 Hify
亮色主题，覆盖 running、completed、manual override、approval/error 与真实
running subagent。无浏览器环境只能记录明确 `ENV-BLOCKED-*`，不能算 PASS。

## 226.8/226.9 Cleanup And Exit

    rtk rg -n "ControlledReActCore|RestrictedReactWorker|processAiAssistantRunWorker|_AUTONOMOUS_WORKER_EXECUTOR|customer_assistant_subagent_bridge|MockAviationAdapter" app frontend/src tests docs specs
    rtk rg -n "app\\.modules\\.(ai_assistant|customer_assistant)" app/modules/agent_harness
    rtk uv run pytest tests/unit/ai_assistant tests/contract/ai_assistant tests/integration/ai_assistant tests/e2e/test_ai_assistant_streaming_e2e.py tests/eval/test_ai_assistant_aggregate_production_eval.py -q --tb=short
    rtk uv run pytest tests/unit/workflow/test_runtime_job_worker.py tests/contract/runtime_jobs tests/integration/runtime_jobs tests/integration/runtime/test_debug_runs_default_async.py -q --tb=short
    rtk uv run ruff check app/modules/ai_assistant app/modules/runtime app/modules/workflow
    rtk npm --prefix frontend run test:unit
    rtk npm --prefix frontend run build
    rtk uv run alembic heads
    rtk git diff --check

Live external model gate: `N/A` for this contract unless separately authorized；
Spec 226 默认 provider call budget 是 0。
