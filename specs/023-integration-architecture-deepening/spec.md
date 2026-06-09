# Spec 023: Integration Architecture Deepening

## Goal

Make Hify cheap and safe to embed into a larger existing system by deepening the
Modules that currently risk horizontal call-site spread:

- host actor, tenant, route, permission, and frontend request integration;
- runtime evidence for reports, audit, and composer debugging;
- resource invocation across Agent, Workflow, Chatflow, Knowledge, MCP tools, and
  subworkflows;
- FlowGraph Node vocabulary and config facts;
- conversation identity, history, and session facts;
- evaluation target invocation and report links;
- persistence lifecycle under a host-managed database.

The objective is not abstract reuse for its own sake. The objective is locality:
changes that belong to one concept should land in one Module, not across every
router, frontend API file, executor, report, and test.

## Why This Spec Exists

Hify has moved beyond the original replica slices. It now has a broad surface:
Agent, Chat, Workflow, Chatflow, Knowledge, MCP, Evaluation, handoff, channels,
observe, and audit. The next integration target is an existing full system with
its own:

- authentication and user identity;
- organization or tenant context;
- role and permission model;
- route/menu/container layout;
- report and dashboard system;
- database migration and deployment lifecycle;
- frontend request gateway.

Without architectural deepening, these host facts would leak into many Hify
callers. That creates coupling, makes reports inconsistent, and makes future
Workflow/Chatflow/Agent changes harder to verify.

## Product Boundary

This spec is an integration-hardening spec. It does not replace 021 or 022.

In scope:

- one backend host integration Module;
- one frontend host request Module;
- one runtime evidence Module shared by observe, audit, composer debug, and
  report adapters;
- central access policy checks for product resources;
- FlowGraph Node catalog deepening;
- unified resource invocation where more than one resource adapter already
  exists or is required by 022;
- evaluation target adapters for Agent, Workflow, and Chatflow report paths;
- persistence lifecycle split between local development and host-managed
  deployment.

Out of scope:

- splitting Workflow and Chatflow into separate runtimes;
- converting the monolith into microservices;
- implementing a full IAM system;
- replacing all existing route contracts;
- changing the `/api/v1/...` envelope contract;
- building a plugin marketplace;
- adding speculative adapters that have only one concrete caller and no 023/022
  slice need.

## Non-Negotiable Architecture Rules

- Keep Workflow and Chatflow on the shared FlowGraph runtime from ADR 0002.
- Do not create a Seam unless there are two adapters or an accepted near-term
  slice that needs the second adapter.
- Every new Module must reduce what callers need to know.
- The Interface is the test surface.
- A Module that only forwards calls without hiding policy, state, or invariants
  fails the deletion test.
- Runtime evidence must be sanitized before it leaves the runtime Module.
- Host actor and tenant facts must not be optional in production mode.
- Startup must not mutate a host-managed database schema outside an explicit
  persistence lifecycle path.

## Current Baseline

| Area | Current State | Integration Gap |
|------|---------------|-----------------|
| Host context | Routers construct domain Modules directly | Actor, tenant, roles, and request id would be duplicated |
| Frontend requests | Axios base is fixed to `/api`; some endpoints use raw `fetch` | Host gateway headers and base URL cannot be injected consistently |
| Audit | Audit actor defaults to `system` | Host reports cannot attribute actions reliably |
| Observe | Observe service reads raw workflow/chatflow/audit tables in router code | Report ownership, permission filtering, and debug projection are shallow |
| Agent access | `access`, `sharing`, `analytics` are JSON shells | No central enforcement or report semantics |
| FlowGraph Node facts | Node type, default config, UI schema, validation, executor switch are spread | Adding `AGENT_CALL` or changing policy requires many edits |
| Resources | Registry lists resources, runtime parses config independently | Resource health, policy, invocation, and evidence drift |
| Conversation state | Chat session/history and Chatflow session/events are separate | Host Conversation Identity and channel reports require joins and duplicated rules |
| Evaluation targets | Evaluation directly constructs ChatService and WorkflowFacade | Target output, target evidence, permission, and debug links are hard to standardize |
| Persistence | App startup calls `create_all` and compatibility `ALTER TABLE` | Host DB lifecycle cannot safely allow hidden runtime DDL |

## Target Architecture

## Slice Evidence

- 023.1 Architecture guardrails and inventory:
  - Inventory: `artifacts/slices/023-integration-architecture-deepening/023.1/inventory.md`
  - RED: `artifacts/slices/023-integration-architecture-deepening/023.1/red.txt`
  - Unit: `artifacts/slices/023-integration-architecture-deepening/023.1/unit.txt`
  - UAT: `artifacts/slices/023-integration-architecture-deepening/023.1/uat.md`
- 023.2 Host Integration Shell and frontend adapter:
  - RED backend: `artifacts/slices/023-integration-architecture-deepening/023.2/red-backend.txt`
  - RED frontend: `artifacts/slices/023-integration-architecture-deepening/023.2/red-frontend.txt`
  - RED run audit tracer: `artifacts/slices/023-integration-architecture-deepening/023.2/red-backend-run-audit.txt`
  - Backend unit/integration: `artifacts/slices/023-integration-architecture-deepening/023.2/backend-regression.txt`
  - Frontend unit: `artifacts/slices/023-integration-architecture-deepening/023.2/frontend-unit.txt`
  - Frontend build: `artifacts/slices/023-integration-architecture-deepening/023.2/frontend-build.txt`
  - E2E: `artifacts/slices/023-integration-architecture-deepening/023.2/e2e-host-request-context.txt`
  - Browser UAT: `artifacts/slices/023-integration-architecture-deepening/023.2/uat.md`
  - Screenshots: `artifacts/slices/023-integration-architecture-deepening/023.2/screenshots/`
- 023.7 Evaluation Target Adapters:
  - Gate summary: `artifacts/slices/023-integration-architecture-deepening/023.7/gate.md`
  - RED: `artifacts/slices/023-integration-architecture-deepening/023.7/red.txt`
  - Unit/build: `artifacts/slices/023-integration-architecture-deepening/023.7/unit.txt`
  - Integration/live LLM: `artifacts/slices/023-integration-architecture-deepening/023.7/integration.txt`
  - E2E: `artifacts/slices/023-integration-architecture-deepening/023.7/e2e.txt`
  - Browser UAT: `artifacts/slices/023-integration-architecture-deepening/023.7/uat.md`
  - Screenshots: `artifacts/slices/023-integration-architecture-deepening/023.7/screenshots/`

### Host Integration Shell

The Host Integration Shell is the first Module at the backend and frontend
Seams.

Backend responsibilities:

- build `RequestContext`;
- validate production host context;
- expose actor, tenant, org, roles, permissions, locale, source, request id;
- mount routers with a stable `/api/v1` contract;
- provide access policy input to Modules;
- attach context to audit and runtime evidence;
- provide local development and test adapters.

Frontend responsibilities:

- centralize base URL, tenant header, auth header, request id, locale, and error
  handling;
- replace raw `fetch` paths for CSV import/export and downloads;
- provide host menu/layout adapters without changing product views;
- keep existing API function names stable for views.

### Access Policy Module

Access Policy is a small policy Module used by Host Integration Shell and
resource Modules. It is not a full IAM implementation.

Policy inputs:

- `RequestContext`;
- resource kind: Agent, Workflow, Chatflow, Knowledge Base, MCP Server,
  Evaluation, Handoff, Runtime Evidence;
- operation: read, create, update, delete, run, publish, share, export, debug;
- resource owner and visibility facts.

Policy outputs:

- allow/deny;
- denial reason;
- sanitized permission metadata for audit.

### Runtime Evidence Module

Runtime Evidence owns data needed by observe, composer debug, audit, and
reports.

Required common fields:

- `ownerType`: AGENT, WORKFLOW, CHATFLOW, EVALUATION, HANDOFF, MCP, KNOWLEDGE;
- `ownerId`;
- `runId` or `eventId`;
- `parentRunId`;
- `nodeKey`;
- `eventType`;
- `status`;
- `actorId`;
- `tenantId`;
- `channel`;
- `sessionId`;
- `conversationId`;
- `resourceType`;
- `resourceId`;
- `latencyMs`;
- `cost` or token estimate when available;
- sanitized input summary;
- sanitized output summary;
- error summary;
- `debugUrl`.

Adapters:

- composer debug adapter for 021;
- report query adapter for host dashboards;
- backward-compatible observe endpoint adapter;
- audit adapter.

### FlowGraph Node Catalog

FlowGraph Node Catalog owns Node vocabulary and Node facts.

Each Node descriptor includes:

- node type;
- display label;
- Flow Type support;
- default config;
- config schema for the right panel;
- control surface descriptors that distinguish selector controls from settings
  panels, so a model dropdown, model gear, skill add button, and prompt inline
  variable picker cannot collapse into one generic schema field;
- input schema;
- output schema;
- runtime executor key;
- resource kinds it can call;
- interrupt behavior;
- publish validation rules;
- debug evidence shape.

The catalog must support existing nodes and make 022 `AGENT_CALL` cheap to add
without scattering facts across frontend and backend.

### Unified Resource Invocation

Unified Resource Invocation deepens the existing Unified Resource concept.

It owns:

- resource descriptors;
- resource type grouping for chooser UIs;
- health and credential status;
- invocation policy;
- timeout and retry behavior;
- write-capable confirmation;
- sanitized input and output summaries;
- runtime evidence;
- adapter selection.

Initial adapters:

- Knowledge Resource adapter;
- MCP Tool adapter;
- API-backed Tool adapter from Spec 024;
- Subworkflow Resource adapter;
- Agent adapter when 022 `AGENT_CALL` reaches implementation.

### Conversation Runtime

Conversation Runtime owns conversation identity and state that crosses Chat and
Chatflow.

It owns:

- Conversation Identity Variable mapping;
- System Variable mapping;
- message history;
- conversation, user, channel, and session variables;
- channel inbound request normalization;
- checkpoint and resume lookup for Chatflow;
- host conversation id mapping.

This Module is delayed until Host Integration Shell and Runtime Evidence are in
place. It should not rewrite Chat or Chatflow first.

### Evaluation Target Adapters

Evaluation Target Adapters own target execution for evaluation and reports.

Target adapters:

- Agent target adapter;
- Workflow target adapter;
- Chatflow target adapter.

Each adapter returns:

- target output;
- status;
- target run id;
- debug URL;
- sanitized evidence;
- target-specific metadata needed by report drilldown.

2026-06-08 MVP implementation note:

- The target adapter Interface and Agent/Workflow/Chatflow adapters are kept in
  `app/modules/evaluation/domain/target_adapters.py` for minimum complexity.
  Split into a `targets/` package only when additional adapters or shared
  runtime evidence logic make the single file too large.
- The case result report now persists and returns `targetType`, `targetRunId`,
  `targetStatus`, `targetDebugUrl`, and `targetEvidenceSummary`.
- Workflow and Chatflow target reports link to the owning full-page canvas debug
  route instead of embedding canvas UI into Evaluation.

### Persistence Lifecycle

Persistence Lifecycle owns schema creation and migration mode.

Modes:

- local development bootstrap: allowed to create missing tables;
- test bootstrap: isolated and deterministic;
- host-managed deployment: no runtime DDL, migrations must run explicitly;
- compatibility check: verify expected columns/tables and fail fast with an
  actionable message.

## Compatibility Requirements

- `/api/v1/...` stays stable.
- Envelope stays `{code, message, data}`.
- Existing frontend views keep using existing `api/*.ts` function names unless a
  slice explicitly migrates them.
- Existing tests remain meaningful and migrate slice by slice.
- Existing observe endpoints can remain as compatibility adapters while 021
  composer debug becomes the primary user path.
- Specs 021 and 022 remain valid. This spec deepens architecture beneath them.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 023.1 Architecture guardrails and inventory | Freeze current shallow call sites and define anti-overdesign gates | RED: guardrail tests/docs fail; Docs: inventory and ADR notes |
| 023.2 Host Integration Shell and frontend adapter | Backend and frontend share host context without per-route copy | RED: context missing tests fail; Integration: actor/tenant/audit; E2E: host headers through UI |
| 023.3 Access Policy Module | Resource operations can be denied centrally and audited | RED: unauthorized run/debug/export tests fail; Integration: Agent/Workflow/Chatflow/Evaluation policy |
| 023.4 Runtime Evidence Module | Runs, events, audit, and debug data share one evidence Interface | RED: report/debug shape tests fail; Integration: Workflow/Chatflow/Agent evidence; E2E: debug link still works |
| 023.5 FlowGraph Node Catalog | Node facts move behind one catalog Interface | RED: catalog contract tests fail; Unit: defaults/schema/control-surface/output validation; E2E: canvas unchanged |
| 023.6 Unified Resource Invocation | Knowledge, MCP, API-backed Tool, and Subworkflow use one invocation evidence/policy path | RED: resource evidence drift tests fail; Integration: MCP/Knowledge/API Tool/Subworkflow calls |
| 023.7 Evaluation Target Adapters | Evaluation targets expose target output, evidence, permission, debug URL | RED: target adapter tests fail; Integration: Agent/Workflow/Chatflow reports |
| 023.8 Conversation Runtime seam | Chat and Chatflow share identity/history mapping where needed | RED: conversation identity tests fail; Integration: Chatflow channel plus Chat session report path |
| 023.9 Persistence Lifecycle and host UAT | Runtime DDL is removed from host mode and host install path is verified | RED: host mode DDL test fails; Integration: schema check; Browser UAT: embedded host smoke |

## Done Criteria

023 is done when:

- Host context crosses backend and frontend through one Interface.
- Actor and tenant appear in audit and runtime evidence.
- Access checks are central for protected resource actions.
- Runtime evidence can power composer debug, observe compatibility endpoints, and
  host reports without raw table knowledge in callers.
- FlowGraph Node facts have one catalog test surface.
- Resource calls produce consistent policy and evidence data.
- Evaluation reports link to target evidence through adapters.
- Host-managed DB mode does not mutate schema at startup.
- Browser UAT proves Hify can run inside a host-style shell with auth headers,
  menu mounting, protected actions, runs, reports, and debug links.
