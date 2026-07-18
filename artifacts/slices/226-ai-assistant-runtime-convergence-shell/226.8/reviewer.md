# Reviewer — 226.8

Verdict: `PASS`

Risk: `high`

Review context: `standard`

Goal trust: `PASS` for 226.8; Spec 226 remains `CONTINUE`

Review basis:

- base: `cae5a5a9`
- branch: `codex/spec-226-agent-harness-convergence`
- merge target: `not-authorized`
- evidence: RED record, inventory, Builder handoff, Checker `ALL GREEN`,
  Browser UAT

## Findings

- severity: critical
  gate: no-op
  action: no-op
  location: `app/modules/ai_assistant/web/router.py`
  evidence: `/worker/process` no longer constructs a worker or calls
    `run_once`; it is enqueue/inspect only.
  recommendation: delete only after external-consumer inventory closes.

- severity: high
  gate: no-op
  action: no-op
  location: `app/core/config.py` and AI runtime composition
  evidence: production defaults to bound capabilities, rejects demo profile,
    and router/standalone worker consume one explicit settings snapshot.
  recommendation: do not add demo capabilities to the production registry.

- severity: high
  gate: no-op
  action: no-op
  location: deterministic no-tool completion
  evidence: fault E2E first reproduced a post-cancel `run.completed`; two
    cancellation gates now prevent terminal completion after control wins.
  recommendation: preserve fault coverage when successful completion is
    consolidated later.

- severity: medium
  gate: no-op
  action: no-op
  location: Customer Assistant domain
  evidence: the misleading one-turn `ControlledReActCore` and unused
    `max_iterations` are gone. The real `RestrictedReactWorker` remains a
    product Adapter over `AgentHarness`.
  recommendation: keep task/profile/policy vocabulary product-local.

- severity: medium
  gate: no-op
  action: no-op
  location: AI Assistant shell and legacy UAT
  evidence: inert Add Context is absent at source and runtime; legacy scripts
    target stable activity identity.
  recommendation: do not reintroduce sequence-range presentation identity.

- severity: low
  gate: non-blocker
  action: no-op
  location: build/test warnings
  evidence: pre-existing Starlette `httpx`, Vite CJS and chunk-size warnings.
  recommendation: handle outside Spec 226.

No Critical or open High finding remains. Recommendation: enter the selective
Slice Commit Gate with only 226.8 implementation, tests, inventory and evidence.
