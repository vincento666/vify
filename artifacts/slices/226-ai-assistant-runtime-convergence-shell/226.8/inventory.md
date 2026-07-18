# 226.8 Production Caller And Deletion Inventory

Inventory date: 2026-07-18

Deletion rule:

```text
no accepted contract
AND no production caller
AND no migration obligation
AND replacement path is green
```

## Customer Assistant Harness Candidates

| Candidate | Production caller / accepted contract | Decision | Physical deletion gate |
|---|---|---|---|
| `ControlledReActCore` | `CustomerAssistantService` needs one Customer-specific recognize/validate/act/finalize coordinator; public Agent Harness owns bounded ReAct | Rename to `CustomerTurnCoordinator`, remove fake `max_iterations` and Harness terminology | Complete in 226.8 |
| `RestrictedReactWorker` | Customer router, configurable worker, live acceptance and SSE path; implements the real Customer Adapter over `AgentHarness` | Keep as product Adapter; do not move business task/model semantics into public Harness | Delete only if Customer production path adopts another tested Harness Adapter |
| `ReactWorkerRegistry` | Router maps persisted worker profiles to `ReactWorkerConfig` | Keep as Customer business configuration; it does not execute iterations or tools | Delete only with the persisted worker-profile contract |
| `tool_policy` | `RestrictedReactWorker` maps Customer policy refs and allowed tools into Harness policy decisions | Keep behind Customer Adapter | Promote only if a second product requires the same policy vocabulary and contract |

Result: Customer Assistant consumes the public Agent Harness without importing
AI Assistant. Product-specific task recognition, worker profile and tool-policy
vocabulary stay local.

## AI Assistant Tool Registry

| Capability | Production evidence | Decision |
|---|---|---|
| workspace read/list/search/edit/write/patch | bound `file_workspace` handlers and Kernel E2E | production profile |
| `run_shell` | bound `subprocess.run(shell=False)` handler with timeout; governed by approval/sandbox policy | production profile |
| `propose_agents_update` | bound diff-preview handler; no direct write before approval | production profile |
| `invoke_skill`, `read_skill_resource` | bound `SkillRuntime` load/read handlers and audit events | production profile |
| child bridge | requires injected `SubagentExecutionProvider`; attaches durable lifecycle/status/result refs | conditionally registered in production |
| `echo_context`, blocked customer update, MockAviation | demo and test callers only | explicit demo profile |
| `search_knowledge_base` | placeholder returns caller-supplied/empty hits; no index Adapter | explicit demo profile |
| `run_skill_script` | only plans a command; does not execute a script | explicit demo profile |

`HIFY_AI_ASSISTANT_TOOL_PROFILE` defaults to `production`; unsupported values
fail validation, and production deployment rejects the `demo` profile. Router
and standalone runtime worker receive the same explicit settings snapshot.

## Product Shell And Projection

| Candidate | Caller / behavior | Decision |
|---|---|---|
| Add Context button | no handler, request field or API contract | removed |
| planning strategy selector | `auto_lightweight`, `deliberate`, `plan_only` drive different runtime plan behavior | kept |
| sequence-range processed group | replaced by stable `runId/activityId` projection in 226.7 | removed; three legacy UAT scripts now use activity selectors |
| historical tool labels | required to render replayed durable audit events, including old/demo runs | kept as presentation compatibility, not executable capability |

## `/worker/process` Compatibility Route

- Repository production caller: none in the frontend.
- Repository callers that remain: compatibility contract/E2E coverage and
  synchronous-run inspection tests.
- Accepted public obligation: `/api/v1/...` compatibility cannot be silently
  removed without external-consumer inventory.
- Current behavior: idempotent enqueue-if-missing plus inspect; request payload
  is ignored; the HTTP process never constructs or runs a worker.
- Metadata: `deprecated=true`,
  `replacement=standalone-runtime-worker`, `sunsetAt=2026-08-01`,
  `removalGate=external-consumer-inventory`.
- Blocker: repository search cannot prove absence of external API consumers.
  Physical deletion is therefore deferred to a separate compatibility
  decision, not treated as cleanup PASS.

## Public Module Boundary Proof

- `app/modules/agent_harness`: bounded ReAct, tool governance, observations and
  terminal semantics; no product imports.
- `app/modules/agent_execution`: parent/child lifecycle contract and durable
  refs; no ReAct, product or UI semantics.
- `app/modules/runtime/domain` and `infra`: job state machine, lease fencing,
  registry and persistence; no business imports.
- `app/modules/runtime/composition.py`: the allowed composition root that
  imports and registers product Adapters.
- AI Assistant and Customer Assistant import the public Modules, never each
  other.
- AI Assistant shell/activity modules remain product-local until a second real
  frontend consumer proves a shared visual invariant.

Executable boundary gates:

```text
tests/contract/agent_harness/test_dependency_direction.py
tests/contract/runtime_jobs/test_runtime_module_boundary.py
```
