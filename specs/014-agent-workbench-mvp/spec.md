# Spec 014: Agent Workbench MVP

## Goal

Turn the current modal-based Agent management page into a product-level Agent
Workbench MVP. The first version should feel like a focused Coze-style builder:
authors can configure identity, model behavior, instructions, capabilities, and
test the Agent in one place, while staying inside the existing Hify runtime
boundary.

This spec does not attempt to clone the full Coze platform. It upgrades the
Agent authoring experience for the capabilities Hify already owns, then leaves
advanced Agent-platform features for later specs.

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

## MVP Core Scope

The MVP prioritizes the smallest set of features that makes Agent authoring
feel product-grade without requiring new orchestration semantics.

| Priority | Capability | MVP Decision |
|----------|------------|--------------|
| P0 | Full-page workbench shell | Add dedicated create/edit routes with header, save state, section navigation, and preview panel. Keep the list page as the management entry. |
| P0 | Identity and model behavior | Move name, description, model, System Prompt, temperature, max tokens, and context turns into the workbench. Reuse existing fields and validation. |
| P0 | Capability cards | Configure MCP tools, knowledge base, and workflow as clear cards with selected state, search/select, status, and links to manage/open resources. |
| P0 | Runtime mode clarity | Show the resolved runtime path and precedence before save/test: workflow > RAG > direct; tools currently run only in direct mode. |
| P0 | Save and validation | Provide dirty state, field-level errors, disabled save for invalid form, backend error surfacing, and unsaved-change guard. |
| P0 | In-workbench preview | Provide an embedded chat preview for the saved Agent using existing chat session and SSE APIs, with reset and mode badges. |
| P1 | Guided empty states | Explain missing model/tool/knowledge/workflow dependencies through action links, not raw error text. |
| P1 | Workbench UAT evidence | Browser UAT must cover create, edit, capability persistence, preview chat, and responsive layout. |

## Deferred Scope

These are intentionally not part of the MVP.

| Later Capability | Reason To Defer |
|------------------|-----------------|
| Multi-Agent orchestration | Requires new runtime model and routing semantics, not only UI. |
| Coze-style publish channels | Needs channel adapters, publish records, and auth/public access decisions. |
| Agent versions/releases | Needs immutable snapshots and migration rules for chat/evaluation references. |
| Memory and variables | Needs durable scoped storage and prompt/runtime contract beyond current context cache. |
| Opening message and suggested questions | Useful, but requires chat product changes and persistence fields not needed for first authoring loop. |
| Prompt optimization/generation | Requires model-backed assistant behavior, cost controls, and auditability. |
| Fine-grained tool policy | Per-tool auth, argument presets, forced/auto/manual mode, and approval gates need a broader tool model. |
| Knowledge retrieval settings | topK, thresholds, rerank, citation behavior, and multi-KB routing belong after RAG behavior is stable. |
| Embedded workflow/chatflow canvas | Reuse links to Workflow/Chatflow first; deeper embedding depends on 011/012 maturity. |
| Evaluation release gate | Evaluation integration should build on 013 after the workbench has stable save/preview behavior. |
| Permissions, sharing, marketplace, analytics | Platform administration features, not needed to prove the core authoring loop. |

## Product Boundary

- The workbench edits the existing Agent resource and preserves `/api/v1/agents`
  compatibility.
- The MVP may add optional read-only helper endpoints or frontend-only adapters,
  but should avoid adding new required Agent database fields unless a slice
  explicitly justifies them.
- The preview panel uses saved Agent state. If there are unsaved changes, the
  user must save before previewing those changes.
- Workflow and RAG behavior must remain compatible with the current chat service.
  If an Agent has both `workflowId` and `knowledgeBaseId`, workflow mode wins and
  the UI must say so.
- Tool binding continues to bind MCP servers as today. Per-tool selection inside
  a server is out of scope.

## User Value

Agent authors can move from "I filled out a database-like form" to "I configured,
validated, and tested an Agent" without leaving the Agent module.

Primary user story:

1. User opens the Agent list and creates a new Agent.
2. User lands in a full-page workbench.
3. User configures identity, model, instructions, and capabilities.
4. User sees the resolved runtime path and any conflicts.
5. User saves, sends a preview message, and sees a streamed answer.
6. User returns to the list with confidence that the Agent is usable.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 014.1 Workbench shell | User can open `/agents/new` and `/agents/{id}/workbench`; layout has header, section navigation, editor area, and preview area | RED: route/UI smoke test fails; Unit: route helpers; Integration: existing Agent list unchanged; E2E: open create/edit workbench; UAT: shell visible |
| 014.2 Core configuration editor | User can create and update existing Agent fields from the workbench with dirty state and field validation | RED: form save test fails; Unit: form adapter/defaults; Integration: create/update contract unchanged; E2E: create/edit/save; UAT: values persist |
| 014.3 Capability cards | User can bind MCP tools, one knowledge base, and one workflow through card/select UI; selected resources persist and show status | RED: capability persistence UI test fails; Unit: capability summary builder; Integration: existing binding endpoints pass; E2E: bind/unbind resources; UAT: cards readable |
| 014.4 Runtime mode clarity | Workbench shows resolved path, precedence warnings, and which capabilities will run during chat | RED: mode summary test fails; Unit: mode resolver mirrors backend; Integration: chat mode tests unchanged; E2E: combined binding warning; UAT: warning visible |
| 014.5 Embedded preview | Saved Agent can be tested from the workbench with streaming response, reset session, and mode badge | RED: preview flow test fails; Unit: preview state machine; Integration: chat session/SSE unchanged; E2E: preview sends message; UAT: answer streams |
| 014.6 Validation and readiness polish | Missing dependency states, backend errors, unsaved-change guard, and responsive layout are production-usable | RED: guard/error UI tests fail; Unit: validation messages; Integration: disabled model/tool errors; E2E: leave guard and error state; UAT: desktop/mobile screenshots |

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
- No raw JSON is required for the MVP workbench.

## Compatibility Rules

- Preserve current Agent list API and response fields.
- Preserve current create/update/delete/tool-binding routes.
- Preserve current chat behavior and SSE event contract.
- Do not remove the Agent list page. It remains the management entry point.
- Existing tests for specs 004, 005, 008, 009, and 010 must continue to pass.

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
