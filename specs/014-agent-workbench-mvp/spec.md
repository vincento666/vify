# Spec 014: Agent Workbench

## Goal

Turn the current modal-based Agent management page into a product-level Agent
Workbench. The implementation is MVP-first, but the product scope includes the
full single-Agent authoring surface: identity, model behavior, instructions,
capabilities, memory, variables, tool policy, knowledge retrieval settings,
preview, release readiness, publishing, and evaluation gates.

The only explicit non-goal is multi-Agent orchestration. Hify may support
workflow and chatflow orchestration, but this spec does not add Coze-style
multi-Agent collaboration, routing, handoff, or group-agent behavior.

## Current Gap

The current Agent module supports CRUD, model selection, System Prompt,
generation parameters, MCP server binding, one knowledge base binding, and one
workflow binding. It is implemented as a table plus create/edit dialog.

That is enough for a management replica, but not enough for a product Agent
Workbench because:

- Agent authors cannot configure and test in the same surface.
- Runtime mode selection is implicit: workflow binding takes priority over RAG,
  RAG takes priority over direct chat, and tool calling only runs on the direct
  path.
- Capability configuration is represented as raw selects/checkboxes, not as
  readable skill cards with status, validation, and next actions.
- There is no first-class place for validation, dirty state, preview sessions,
  or launch readiness.

## Scope And Priority

The first implementation milestone prioritizes the smallest set of features that
makes Agent authoring feel product-grade without requiring new orchestration
semantics. Later milestones stay inside this spec and complete the rest of the
single-Agent workbench.

| Priority | Capability | Decision |
|----------|------------|--------------|
| P0 | Full-page workbench shell | Add dedicated create/edit routes with header, save state, section navigation, and preview panel. Keep the list page as the management entry. |
| P0 | Identity and model behavior | Move name, description, model, System Prompt, temperature, max tokens, and context turns into the workbench. Reuse existing fields and validation. |
| P0 | Capability cards | Configure MCP tools, knowledge base, and workflow as clear cards with selected state, search/select, status, and links to manage/open resources. |
| P0 | Runtime mode clarity | Show the resolved runtime path and precedence before save/test: workflow > RAG > direct; tools currently run only in direct mode. |
| P0 | Save and validation | Provide dirty state, field-level errors, disabled save for invalid form, backend error surfacing, and unsaved-change guard. |
| P0 | In-workbench preview | Provide an embedded chat preview for the saved Agent using existing chat session and SSE APIs, with reset and mode badges. |
| P1 | Guided empty states | Explain missing model/tool/knowledge/workflow dependencies through action links, not raw error text. |
| P1 | Workbench UAT evidence | Browser UAT must cover create, edit, capability persistence, preview chat, and responsive layout. |
| P2 | Opening message and suggested questions | Add persisted welcome copy and starter questions, then surface them in chat and preview. |
| P2 | Agent versions/releases | Add immutable snapshots so preview, evaluation, and publishing can target stable Agent versions. |
| P2 | Publish channels | Add API/channel publishing shells and publish records; real external adapters can land incrementally. |
| P2 | Memory and variables | Add workbench-managed variables and durable memory scopes for single-Agent chat behavior. |
| P2 | Prompt optimization/generation | Add model-backed prompt drafting/optimization with explicit user approval and audit trail. |
| P2 | Fine-grained tool policy | Add per-tool visibility, call mode, argument presets, approval policy, and error behavior. |
| P2 | Knowledge retrieval settings | Add topK, score threshold, rerank option, citation style, and multi-KB selection once RAG settings are stable. |
| P3 | Flow authoring link | Deep-link to mature 011/012 full-page Workflow/Chatflow canvas editing from the capability card. Inline embedding is allowed only as a full-screen route/split mode, not as a small card embed. |
| P3 | Evaluation release gate | Connect 013 Evaluation so an Agent version can require passing experiments before release. |
| P3 | Permissions, sharing, catalog, analytics | Add owner/access fields, share controls, catalog/marketplace shell, usage metrics, and quality telemetry. |

## Explicit Non-Scope

- Multi-Agent orchestration is not part of this spec.
- Do not add Agent-to-Agent handoff, group chat, planner/worker Agent teams, or
  cross-Agent routing.
- If a future feature needs multiple LLM/tool steps, use Workflow or Chatflow
  rather than adding a multi-Agent runtime here.

## Product Boundary

- The workbench edits the existing Agent resource and preserves `/api/v1/agents`
  compatibility.
- The first milestone may add optional read-only helper endpoints or frontend-only adapters,
  but should avoid adding new required Agent database fields unless a slice
  explicitly justifies them.
- The preview panel uses saved Agent state. If there are unsaved changes, the
  user must save before previewing those changes.
- Workflow and RAG behavior must remain compatible with the current chat service.
  If an Agent has both `workflowId` and `knowledgeBaseId`, workflow mode wins and
  the UI must say so.
- Baseline tool binding continues to bind MCP servers as today. Later slices may
  add per-tool policy after MCP tool metadata is represented in a durable shape.
- Publishing, versioning, variables, memory, and evaluation gates may add schema
  in later slices, but each slice must preserve existing Agent API compatibility
  or introduce additive routes.

## User Value

Agent authors can move from "I filled out a database-like form" to "I configured,
validated, and tested an Agent" without leaving the Agent module.

Primary user story:

1. User opens the Agent list and creates a new Agent.
2. User lands in a full-page workbench.
3. User configures identity, model, instructions, capabilities, memory, and
   optional release settings as the slices mature.
4. User sees the resolved runtime path and any conflicts.
5. User saves, sends a preview message, and sees a streamed answer.
6. User evaluates or publishes a stable Agent version when the later slices are
   complete.
7. User returns to the list with confidence that the Agent is usable.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 014.1 Workbench shell | User can open `/agents/new` and `/agents/{id}/workbench`; layout has header, section navigation, editor area, and preview area | RED: route/UI smoke test fails; Unit: route helpers; Integration: existing Agent list unchanged; E2E: open create/edit workbench; UAT: shell visible |
| 014.2 Core configuration editor | User can create and update existing Agent fields from the workbench with dirty state and field validation | RED: form save test fails; Unit: form adapter/defaults; Integration: create/update contract unchanged; E2E: create/edit/save; UAT: values persist |
| 014.3 Capability cards | User can bind MCP tools, one knowledge base, and one workflow through card/select UI; selected resources persist and show status | RED: capability persistence UI test fails; Unit: capability summary builder; Integration: existing binding endpoints pass; E2E: bind/unbind resources; UAT: cards readable |
| 014.4 Runtime mode clarity | Workbench shows resolved path, precedence warnings, and which capabilities will run during chat | RED: mode summary test fails; Unit: mode resolver mirrors backend; Integration: chat mode tests unchanged; E2E: combined binding warning; UAT: warning visible |
| 014.5 Embedded preview | Saved Agent can be tested from the workbench with streaming response, reset session, and mode badge | RED: preview flow test fails; Unit: preview state machine; Integration: chat session/SSE unchanged; E2E: preview sends message; UAT: answer streams |
| 014.6 Validation and readiness polish | Missing dependency states, backend errors, unsaved-change guard, and responsive layout are production-usable | RED: guard/error UI tests fail; Unit: validation messages; Integration: disabled model/tool errors; E2E: leave guard and error state; UAT: desktop/mobile screenshots |
| 014.7 Chat entry polish | Agent has opening message and suggested questions visible in preview and chat create flow | RED: starter UI test fails; Unit: schema defaults; Integration: persisted fields; E2E: starter question sends; UAT: welcome state visible |
| 014.8 Version and release snapshots | User can create immutable Agent versions and select draft/latest/released in preview | RED: version contract test fails; Unit: snapshot builder; Integration: version persistence; E2E: create release; UAT: version selector works |
| 014.9 Publish channels | User can publish a released Agent to API/channel shells and see publish status | RED: publish route/UI test fails; Unit: publish guard; Integration: publish records; E2E: publish/unpublish; UAT: publish state visible |
| 014.10 Memory and variables | User can define single-Agent variables and memory scopes used by chat prompt/runtime | RED: variable/memory tests fail; Unit: resolver; Integration: chat injection; E2E: variable affects answer; UAT: memory panel usable |
| 014.11 Prompt optimization | User can ask a model to draft or improve instructions, review the diff, and apply manually | RED: prompt optimizer test fails; Unit: diff/apply state; Integration: provider-backed draft call; E2E: generate/apply; UAT: approval flow visible |
| 014.12 Tool policy | User can configure per-tool visibility, call policy, argument presets, approval, timeout, and failure behavior | RED: tool policy contract fails; Unit: policy merger; Integration: chat tool runner honors policy; E2E: policy blocks/allows call; UAT: policy card works |
| 014.13 Knowledge retrieval settings | User can select multiple knowledge bases and configure topK, score threshold, rerank, and citation style | RED: retrieval settings tests fail; Unit: retrieval config validation; Integration: RAG honors settings; E2E: settings persist; UAT: retrieval summary visible |
| 014.14 Flow authoring link | User can open/edit linked Workflow or Chatflow from the Agent workbench after 011/012 are stable | RED: flow authoring route test fails; Unit: link/full-screen guard; Integration: graph save unaffected; E2E: open linked canvas route; UAT: deep-link or full-screen path works |
| 014.15 Evaluation release gate | User can require selected 013 experiments to pass before release/publish | RED: release gate test fails; Unit: gate evaluator; Integration: evaluation result lookup; E2E: failed gate blocks release; UAT: gate status visible |
| 014.16 Access, sharing, catalog, analytics | User can manage owner/access, share/catalog visibility, and inspect basic usage/quality telemetry | RED: access/analytics tests fail; Unit: policy summary; Integration: access records and metrics; E2E: share/inspect metrics; UAT: admin shell visible |

## UX Requirements

- Workbench header shows Agent name, status, save state, back action, and primary
  save/test actions.
- Section navigation is task-oriented: Overview, Instructions, Capabilities,
  Preview. It may be tabs or a left rail, but must not hide the preview behind a
  modal.
- The editor area uses compact operational UI, not a marketing page.
- Capability cards show current resource name, enabled/disabled/missing state,
  and next action.
- Preview panel must remain visible on desktop and collapse into an accessible
  drawer or tab on small screens.
- The page must communicate runtime precedence before the user tests a message.
- No raw JSON is required for the workbench unless an advanced developer drawer
  is explicitly added in a later slice.

## Flow Authoring Boundary

The 2026-06-01 Coze canvas audit shows Workflow authoring as a full-page canvas route with compact top chrome, right node config panel, centered bottom toolbar, and bottom debug dock. For Agent workbench:

- Capability cards may show the linked Workflow/Chatflow name, status, validation state, and `打开画布` action.
- Opening a linked flow should navigate or deep-link to the 011/012 full-page canvas route, preserving Agent workbench return context.
- A future embedded mode must use a full-screen or split-pane canvas shell that preserves the Coze-like toolbar, right panel, ports, and bottom debug dock.
- Do not embed the canvas inside a small card, modal preview, or marketing-style panel; that would break node dragging, bottom toolbar placement, and pixel fidelity.

## Compatibility Rules

- Preserve current Agent list API and response fields.
- Preserve current create/update/delete/tool-binding routes.
- Preserve current chat behavior and SSE event contract.
- Do not remove the Agent list page. It remains the management entry point.
- Existing tests for specs 004, 005, 008, 009, and 010 must continue to pass.
- Later schema additions must be additive and must not break existing draft
  Agents created before this spec.

## Evidence

Slice evidence goes under:

```text
artifacts/slices/014-agent-workbench-mvp/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```
