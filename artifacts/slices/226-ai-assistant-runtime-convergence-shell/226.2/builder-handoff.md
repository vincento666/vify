# Builder Handoff — 226.2

TDD method: `tdd`

## Scope

- Routed the AI Assistant live production ReAct loop through the public
  `AgentHarness.execute` Interface while retaining its planner, prompt/memory,
  scheduled parallel tool execution, ToolRunner ledger, approval, streaming,
  and terminal-result behavior behind an AI Assistant Adapter.
- Added optional Harness batch invocation so the existing scheduler retains its
  bounded read parallelism. The public Harness authorizes the whole batch before
  any invocation.
- Added product-neutral `agent_execution` child-reference types.
- Added a Customer Assistant child-execution Adapter and injected it from the
  application composition root.
- Removed all AI Assistant imports of Customer Assistant.

## RED

- `red-ai-adapter.txt`: no public Harness injection seam.
- `red-dependency.txt`: AI Assistant imported Customer Assistant.
- `reviewer-repair-red.txt`: partial batch authorization allowed an earlier
  call to execute before a later denial.

## GREEN Evidence

```text
rtk uv run pytest tests/contract/agent_harness tests/unit/ai_assistant tests/unit/customer_assistant/test_react_worker.py -q --tb=short
128 passed, 16 subtests passed

rtk uv run pytest tests/integration/ai_assistant tests/integration/customer_assistant -q --tb=short
118 passed, 1 skipped, 14 subtests passed

rtk uv run pytest tests/contract/test_ai_assistant_live_qwen_api.py -q --tb=short
5 passed

rtk uv run pytest tests/contract/test_ai_assistant_customer_bridge_api.py -q --tb=short
1 passed

rtk uv run ruff check app/modules/agent_execution app/modules/agent_harness app/modules/ai_assistant app/modules/customer_assistant app/main.py
All checks passed

rtk git diff --check -- <226.2 scoped paths>
PASS
```

## Explicit N/A Gates

- Browser UAT: N/A. This foundation slice changes no frontend or public user
  interaction.
- Database migration: N/A. No schema or persistence contract changed.
- Live provider: N/A. Contract provider budget is zero; deterministic live-model
  contracts cover the Adapter.
- Deployment: N/A and not authorized.

## Safety And Remaining Contract

- The AI Adapter currently delegates detailed permission/sandbox/approval to the
  existing scheduled ToolRunner; 226.4 owns extraction of the trusted principal
  and policy boundary. This slice does not claim P0 security completion.
- The new Agent Execution type represents child references only. Real durable
  child lifecycle/presence remains 226.6.
- No production data, migration apply, deployment, provider call, push, PR,
  or merge action occurred.
- Pre-existing unrelated worktree changes were not staged, rewritten, or
  removed.
