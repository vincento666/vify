# Tasks 023: Integration Architecture Deepening

## 023.1 Architecture guardrails and inventory

- [x] RED: add failing tests or checks that document current shallow seams.
- [x] Inventory router construction sites that need `RequestContext`.
- [x] Inventory frontend raw `fetch` and fixed base URL paths.
- [x] Inventory observe/report/debug raw table projections.
- [x] Inventory Node facts split across frontend defaults, config schema, validation, and backend executor switch.
- [x] Inventory resource invocation paths for Knowledge, MCP Tool, Subworkflow, and Agent.
- [x] Inventory runtime DDL in startup and compatibility schema paths.
- [x] Write `artifacts/slices/023-integration-architecture-deepening/023.1/inventory.md`.
- [x] Add anti-overdesign checklist to the inventory.
- [x] Gates pass.

## 023.2 Host Integration Shell and frontend adapter

- [x] RED: backend request context tests fail because actor and tenant are unavailable.
- [x] RED: frontend request tests fail because raw `fetch` bypasses host headers.
- [x] Add `RequestContext` model with actor, tenant, org, roles, permissions, request id, source, and locale.
- [x] Add local dev adapter and host header adapter.
- [x] Add FastAPI dependency for `RequestContext`.
- [x] Thread `RequestContext` into audit recording for at least Agent, Workflow, Chatflow, and Evaluation write/run operations.
- [x] Add frontend host runtime config for API base URL and header injection.
- [x] Route `frontend/src/utils/request.ts` through host adapter while preserving existing exported methods.
- [x] Replace CSV import/export raw `fetch` with host-aware request helpers.
- [x] Integration green: actor and tenant are visible in audit rows.
- [x] E2E green: host headers reach backend from UI actions.
- [x] Browser UAT: embedded host-style shell can list and run one Workflow.
- [x] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.2/`.
- [x] Gates pass.

## 023.3 Access Policy Module

- [ ] RED: protected debug/export/run action succeeds without required permission.
- [ ] Add protected operation model for resource kind and operation.
- [ ] Add access policy Interface returning allow/deny and denial reason.
- [ ] Add local permissive adapter for dev mode.
- [ ] Add host permission adapter based on `RequestContext.permissions`.
- [ ] Add compatibility adapter that can read Agent `access` JSON where needed.
- [ ] Enforce policy for Workflow run/publish/debug.
- [ ] Enforce policy for Chatflow run/resume/publish/debug.
- [ ] Enforce policy for Agent run/publish/share/debug.
- [ ] Enforce policy for Evaluation run/export.
- [ ] Record denied actions in audit with actor and tenant.
- [ ] Contract green: denied responses keep `{code, message, data}` envelope.
- [ ] E2E green: unauthorized host user sees action blocked.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.3/`.
- [ ] Gates pass.

## 023.4 Runtime Evidence Module

- [ ] RED: composer debug/report tests fail because evidence lacks owner, actor, or tenant.
- [ ] Add runtime evidence model and projection DTO.
- [ ] Add evidence facade for run detail and report listing.
- [ ] Project Workflow run/node run data into evidence DTO.
- [ ] Project Chatflow session/event/checkpoint data into evidence DTO.
- [ ] Project Agent preview/chat run data where available.
- [ ] Project resource calls and handoff events into evidence DTO.
- [ ] Sanitize input/output/error summaries in one place.
- [ ] Add `debugUrl` generation for Workflow, Chatflow, and Agent owner routes.
- [ ] Migrate observe route implementation to evidence facade as a compatibility adapter.
- [ ] Add host report query filters: owner type/id, actor, tenant, channel, status, date range.
- [ ] Integration green: Workflow and Chatflow run detail share one evidence shape.
- [ ] E2E green: composer debug link still opens owner page.
- [ ] Browser UAT: report list and debug detail show sanitized data.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.4/`.
- [ ] Gates pass.

## 023.5 FlowGraph Node Catalog

- [ ] RED: Node catalog contract tests fail because descriptors do not exist.
- [ ] Add backend Node descriptor model with type, flow support, output schema, executor key, validation rules, and evidence shape.
- [ ] Add descriptors for existing Workflow/Chatflow nodes.
- [ ] Add catalog control-surface descriptors for selector-vs-settings behavior, including LLM model selector, model gear panel, skill add tabs, and inline prompt variable trigger.
- [ ] Add unit tests for default output schemas and publish validation rules.
- [ ] Move backend executor lookup toward catalog-based registry without changing behavior.
- [ ] Add frontend Node catalog with label, default config, config panel sections, and output parameters.
- [ ] Refactor `flowGraph.ts` defaults to use catalog data.
- [ ] Refactor `nodeConfig.ts` schemas to use catalog data.
- [ ] Keep `workflowValidation.ts` behavior green.
- [ ] E2E green: existing canvas create/edit/run behavior unchanged.
- [ ] Browser UAT: Workflow and Chatflow canvas look unchanged.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.5/`.
- [ ] Gates pass.

## 023.6 Unified Resource Invocation

- [ ] RED: resource invocation evidence tests fail because MCP/Knowledge/API-backed Tool/Subworkflow differ.
- [ ] Add ResourceRef, ResourcePolicy, InvocationContext, resource type grouping, and ResourceInvocationResult models.
- [ ] Add Knowledge Resource adapter with source-aware evidence compatibility.
- [ ] Add MCP Tool adapter with timeout, retry, write-capable policy, sanitized input/output, and latency.
- [ ] Add API-backed Tool adapter from Spec 024 with the same sanitized evidence contract.
- [ ] Add Subworkflow Resource adapter with nested run id, recursion guard handoff, and mapped input/output summaries.
- [ ] Route Workflow `TOOL_CALL` through Unified Resource Invocation.
- [ ] Route Workflow/Chatflow `KNOWLEDGE` node through Unified Resource Invocation.
- [ ] Route `EXECUTE_WORKFLOW` evidence through Unified Resource Invocation without breaking current runtime.
- [ ] Keep existing resource registry response compatible.
- [ ] Integration green: MCP/Knowledge/API-backed Tool/Subworkflow calls produce consistent evidence.
- [ ] E2E green: tool and knowledge nodes still run.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.6/`.
- [ ] Gates pass.

## 023.7 Evaluation Target Adapters

- [x] RED: Evaluation target tests fail because target result lacks debug URL/evidence.
- [x] Add target adapter Interface for Agent, Workflow, and Chatflow.
- [x] Move Agent target execution out of direct `ChatService` construction in EvaluationService.
- [x] Move Workflow/Chatflow target execution behind target adapters.
- [x] Return target output, target run id, status, debug URL, and evidence summary.
- [x] Apply Access Policy before running a target.
- [x] Persist target evidence summary in evaluation case results.
- [x] Update run report DTO to include target evidence link when available.
- [x] Integration green: Agent, Workflow, and Chatflow experiments still run.
- [x] E2E green: failed case report links back to owning target debug detail.
- [x] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.7/`.
- [x] Gates pass.

## 023.8 Conversation Runtime seam

- [ ] RED: conversation identity tests fail because Chat and Chatflow normalize identities differently.
- [ ] Add conversation runtime Interface for System Variables and Conversation Identity Variable.
- [ ] Add channel inbound normalization adapter.
- [ ] Add message history lookup Interface.
- [ ] Add session report projection for Chat and Chatflow.
- [ ] Migrate Chatflow run input construction to use the conversation runtime shape.
- [ ] Keep Chat session storage and Chatflow session storage separate unless tests prove storage merge is needed.
- [ ] Integration green: Chatflow channel invocation and resume still work.
- [ ] Integration green: host report can query by conversation id across Chat and Chatflow evidence.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.8/`.
- [ ] Gates pass.

## 023.9 Persistence Lifecycle and host UAT

- [ ] RED: host mode startup test fails if runtime DDL is attempted.
- [ ] Add persistence mode setting: local, test, host, check.
- [ ] Move `create_all` local bootstrap behind local/test modes.
- [ ] Move compatibility `ALTER TABLE` logic behind explicit local compatibility path.
- [ ] Add host schema check that fails fast with missing table/column details.
- [ ] Keep Alembic migration tests green.
- [ ] Add deployment doc for host-managed migrations.
- [ ] E2E green: app starts in local mode unchanged.
- [ ] Integration green: host mode does not mutate schema at startup.
- [ ] Browser UAT: host-style smoke covers login headers, menu mount, protected action, run, report, and debug link.
- [ ] Save evidence under `artifacts/slices/023-integration-architecture-deepening/023.9/`.
- [ ] Gates pass.

## Final gate

- [ ] Full backend unit/integration/contract suite green.
- [ ] Full frontend unit suite green.
- [ ] Relevant E2E suite green.
- [ ] Browser UAT evidence saved.
- [ ] `spec.md`, `plan.md`, and `tasks.md` updated with final evidence.
- [ ] Architecture report or ADR updated if any 023 decision changes ADR 0002, 021, or 022.
