# Plan 023: Integration Architecture Deepening

## Strategy

This is a staged deepening refactor. Do not perform a big-bang rewrite.

Move one concept at a time behind a deeper Interface, keep existing route
contracts, and preserve existing behavior through compatibility adapters.

The order matters:

1. Host Integration Shell first, because every other Module needs actor and
   tenant context.
2. Access Policy second, because host context needs an enforcement point.
3. Runtime Evidence third, because reports, audit, and debug must share owner
   and actor facts.
4. FlowGraph Node Catalog before broad node changes such as `AGENT_CALL`.
5. Unified Resource Invocation once evidence and policy shape exists.
6. Evaluation Target and Conversation Runtime after evidence can link back to
   owners and runs.
7. Persistence Lifecycle before host deployment.

## Anti-Overdesign Gates

Before adding any new Module or Interface, answer:

- Which three call sites get simpler?
- Which duplicated rule moves behind the Interface?
- Which second adapter makes the Seam real?
- Which tests move from implementation internals to the Interface?
- What code can be deleted or made dumb?

If the answer is weak, keep the code local.

## Target Modules

### Host Integration Shell

Recommended package:

```text
app/core/host/
├── context.py
├── adapters.py
├── dependencies.py
├── policy.py
└── frontend_contract.md
```

Suggested backend types:

```python
RequestContext(
    actor_id: str,
    actor_name: str,
    tenant_id: str,
    org_id: str,
    roles: tuple[str, ...],
    permissions: tuple[str, ...],
    request_id: str,
    source: str,
    locale: str,
)
```

Adapters:

- local dev adapter: default actor and tenant;
- test adapter: explicit context injection;
- host header adapter: extracts actor, tenant, roles, permissions, request id.

Do not bake one host system into this Module. Keep host-specific parsing in an
adapter.

023.2 completion notes:

- Backend `RequestContext` now lives under `app/core/host/` and is injected by
  FastAPI dependencies.
- `AuditRepository.record` accepts `request_context` and merges actor plus
  `metadata.requestContext`.
- Workflow/Chatflow run and publish/channel audits, Agent write audits, and
  Evaluation create/run audits carry host actor and tenant.

### Frontend Host Adapter

Recommended package:

```text
frontend/src/host/
├── context.ts
├── request.ts
├── menu.ts
└── runtimeConfig.ts
```

Migration path:

1. Keep `frontend/src/utils/request.ts` as the public request facade.
2. Move implementation details into `frontend/src/host/request.ts`.
3. Route raw `fetch` upload/CSV/SSE paths through `hostFetch`.
4. Keep `/api` as the default local adapter; host shell may provide
   `__HIFY_HOST__` or `hifyHostContext` runtime config.
3. Replace raw `fetch` in import/export paths.
4. Add runtime config for base URL and header injection.
5. Keep existing `frontend/src/api/*.ts` function names.

### Access Policy Module

Place core policy near Host Integration Shell, but keep product resource facts
out of generic host parsing.

Recommended flow:

```text
RequestContext -> AccessPolicy -> ProtectedOperation -> allow/deny -> audit
```

Start with these operations:

- Agent: read, update, run, publish, share, debug;
- Workflow: read, update, run, publish, debug;
- Chatflow: read, update, run, publish, resume, debug;
- Evaluation: read, run, export;
- Runtime Evidence: read, debug, export.

Do not build full ownership UI in this slice. Use existing `access` JSON fields
as one adapter until a real host authorization adapter exists.

### Runtime Evidence Module

Recommended package:

```text
app/modules/runtime_evidence/
├── domain/
│   ├── model.py
│   ├── service.py
│   └── projection.py
├── infra/
│   └── repository.py
└── api/
    └── facade.py
```

Initial implementation can project from existing tables instead of migrating all
storage immediately.

Interface examples:

- `record_run_started(...)`
- `record_run_finished(...)`
- `record_node_event(...)`
- `record_resource_call(...)`
- `get_debug_detail(owner_type, owner_id, run_id, context)`
- `list_report_runs(filters, context)`

Projection rules:

- sanitize inputs and outputs once;
- add actor and tenant from `RequestContext`;
- preserve existing observe compatibility route;
- make 021 composer debug endpoints read from this Module.

### FlowGraph Node Catalog

Recommended backend package:

```text
app/modules/workflow/domain/node_catalog.py
```

Recommended frontend package:

```text
frontend/src/views/workflow/nodeCatalog.ts
```

Migration path:

1. Add catalog descriptors for current nodes.
2. Make tests assert default config, config schema, outputs, publish validation,
   and executor key from the catalog.
3. Move frontend labels/defaults/config sections to frontend catalog.
4. Move backend executor switch to catalog-based registry.
5. Add `AGENT_CALL` through catalog only after current behavior is green.

Keep descriptors explicit. Do not generate complex schemas prematurely.

### Unified Resource Invocation

Recommended package:

```text
app/modules/resource_invocation/
├── domain/
│   ├── model.py
│   ├── policy.py
│   ├── service.py
│   └── evidence.py
├── adapters/
│   ├── knowledge.py
│   ├── mcp.py
│   ├── subworkflow.py
│   └── agent.py
└── api/
    └── facade.py
```

Invocation Interface:

```python
invoke_resource(
    resource_ref: ResourceRef,
    input_values: dict[str, Any],
    policy: ResourcePolicy,
    context: InvocationContext,
) -> ResourceInvocationResult
```

Do first:

- use it for MCP Tool evidence and policy;
- use it for Knowledge evidence;
- use it for Subworkflow evidence.

Do later:

- add Agent adapter when 022 `AGENT_CALL` implementation starts.

### Evaluation Target Adapters

Recommended package:

```text
app/modules/evaluation/domain/targets/
├── base.py
├── agent.py
├── workflow.py
└── chatflow.py
```

Target Interface:

```python
run_target(
    target_id: int,
    mapped_input: dict[str, Any],
    context: EvaluationTargetContext,
) -> EvaluationTargetResult
```

Result includes:

- text output;
- status;
- target run id;
- debug URL;
- evidence summary;
- error message.

2026-06-08 implementation decision:

- The MVP keeps the Interface and concrete Agent/Workflow/Chatflow adapters in
  `app/modules/evaluation/domain/target_adapters.py` rather than introducing a
  package tree immediately. This still removes direct `ChatService`
  construction from `EvaluationService`, standardizes report evidence, and keeps
  the slice small enough for the current 013/023 target-link requirement.
- Expand to the recommended `targets/` package when 023.4 Runtime Evidence or a
  new target type creates real file pressure.
- Evidence: `artifacts/slices/023-integration-architecture-deepening/023.7/`.

### Conversation Runtime

Do not start by merging tables.

Start with an Interface that normalizes conversation facts:

- inbound channel request to System Variables;
- Conversation Identity Variable mapping;
- message history lookup;
- session report projection.

Only migrate storage if tests prove the current split causes report or resume
bugs.

### Persistence Lifecycle

Recommended package:

```text
app/core/persistence/
├── lifecycle.py
├── schema_check.py
└── bootstrap.py
```

Modes:

- `local`: may create missing tables;
- `test`: may create isolated schema;
- `host`: must not run DDL at startup;
- `check`: validate schema and fail fast.

Move compatibility `ALTER TABLE` behavior out of default startup for host mode.

## Testing Strategy

Every slice keeps RED evidence.

Test levels:

- Unit: Module Interface behavior and anti-overdesign guardrails.
- Integration: router/context/policy/evidence/resource flows.
- Contract: `/api/v1` envelope and route compatibility.
- E2E: host headers, protected action denial, run/debug/report path.
- Browser UAT: host-style shell, menu, run, report, debug link.

Evidence path:

```text
artifacts/slices/023-integration-architecture-deepening/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── contract.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

## Rollout Notes

- Do not delete old observe endpoints until 021 composer debug and host report
  adapters pass.
- Do not remove local dev defaults. They are adapters, not production policy.
- Keep frontend API function names stable during host request refactor.
- Keep `Flow Type` visible in product language: Workflow List and Chatflow List
  remain separate.
- Keep Agent access JSON as compatibility data until Access Policy has a host
  adapter.
