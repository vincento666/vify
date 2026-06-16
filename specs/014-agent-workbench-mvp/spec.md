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

## Live Coze Agent Detail Alignment

The 2026-06-02 in-app browser audit of the Coze Agent detail page observed a
three-column Agent authoring surface, captured at
`artifacts/research/coze-agent-detail/spec-014-live-audit-20260602.md`.

The Coze layout differs from Hify's current 014 shell in one important way:
desktop Agent detail is not primarily "left navigation + center editor + right
preview". It is:

1. Left column: `人设与回复逻辑`
   - persona and reply-logic authoring surface.
   - prompt helper/action icons.
   - prompt template cards with `推荐` / `个人` tabs and examples such as
     `通用结构`, `任务执行`, and `角色扮演`.
2. Middle column: `编排`
   - model settings.
   - skills: plugins/tools and workflows.
   - knowledge: text, table, image/photo knowledge.
   - memory: variables, database, long-term memory, file box.
   - conversation experience: opening message, user question suggestions, and
     shortcut commands.
3. Right column: `预览与调试`
   - always-visible preview chat.
   - process/log/config controls.
   - bot avatar/name, input composer, add action, microphone, and generated
     content disclaimer.

Header observations:

- Back action, Agent avatar/name/edit action, Agent mode selector, autosave
  timestamp, history/refresh-like utility action, and primary `发布`.
- Visible mode label: `单 Agent（自主规划模式）`.
- Draft state is communicated with autosave text, not only a manual save button.

Implication for Hify:

- Keep the Agent list as the entry point.
- Keep the right preview/debug panel.
- Reorganize desktop workbench toward Coze's left persona editor + middle
  orchestration stack + right preview/debug.
- Move section navigation into compact tabs, anchors, or a collapsible secondary
  control so it does not consume the primary left column.
- Workflow/Chatflow capability cards still open the full 011/012 canvas route;
  do not embed the canvas inside the Agent detail columns.

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
| P3 | Coze three-column lifecycle alignment | Reorganize the workbench into persona/reply logic, orchestration, and preview/debug columns, then connect draft autosave, testing, versioning, and publishing into one lifecycle. |

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
| 014.17 Coze three-column lifecycle alignment | Agent detail desktop layout matches Coze's left persona/reply logic, middle orchestration stack, and right preview/debug lifecycle | RED: layout/lifecycle tests fail; Unit: shell state; Integration: existing Agent contracts unchanged; E2E: configure, preview, version, publish path; UAT: screenshots against Coze audit |
| 014.19 Agent detail MVP trim and real-provider direct mode | Agent detail removes non-MVP Coze shell content, keeps release/access in the publish lifecycle dialog, and defaults direct preview/chat to the real configured provider | RED: shell trim and tool-policy E2E fail; Unit: Agent shell/tool policy; Integration: Agent/tool contracts; E2E: full Agent workbench matrix; UAT: browser screenshots and real model binding |
| 014.20 Agent detail usability trim | Agent detail fixes persona editor sizing, preview empty-state styling, runtime wording, MCP selection density, and publish-dialog primary/advanced separation | RED: browser UAT visual checks fail; Unit: runtime wording; E2E: capability selection, lifecycle, publish, preview, tool policy; UAT: screenshots and browser metrics |
| 014.21 Preview debug detail panel | Agent preview replaces shell header controls with a functional debug icon, opens a Coze-like right-side debug detail panel, and uses horizontal scrolling so the fourth column does not squeeze the existing three-column workbench | RED: debug layout squeezes columns; Unit: Agent shell tests; E2E: lifecycle/preview/publish; UAT: browser width metrics and screenshots |
| 014.22 Agent configuration effective UAT | Agent workbench trims redundant LLM/runtime chrome, aligns icon buttons with the canvas toolbar system, and proves persona/orchestration settings are real through API and LLM-backed gates | RED: header/icon UI assertions fail; Unit: Agent helpers; E2E: lifecycle/core/runtime/preview/memory/chat-entry/version/capability/retrieval/tool/prompt/flow; UAT: browser visual metrics |
| 014.23 Preview opening message and bottom starters | Workbench Preview shows the configured opening message as the first assistant line and keeps suggested starters bottom-aligned and visually distinct | RED: opening message absent from preview; Unit: Agent helper tests; E2E: chat-entry real LLM path; UAT: browser layout metrics |
| 014.24 MCP/RAG runtime proof and preview composer polish | MCP tool policy and knowledge retrieval are proven effective, while Workbench Preview uses assistant opening bubbles, right-bottom starter bubbles, adaptive message widths, a two-part composer without a middle divider, and debug details backed by real preview-run data | RED: provider paging/tool-policy and preview visual assertions fail; Unit: Agent helpers; Integration: tool policy and RAG retrieval; E2E: tool policy, preview debug, core config, memory variables, and chat entry; UAT: browser layout metrics |

## UX Requirements

- Workbench header shows Agent name, status, save state, back action, and primary
  save/test actions.
- Desktop workbench uses three primary columns after 014.17:
  - left: persona and reply logic.
  - middle: orchestration stack.
  - right: preview and debug.
- After 014.19, the MVP Agent detail removes top anchor tabs from the desktop
  surface. The header owns Agent name editing; the left persona column is pure
  System Prompt / reply logic; `版本与发布`, `发布渠道`, `访问与分享`, and analytics
  belong to the `发布` lifecycle dialog instead of the orchestration column.
- After 014.20, runtime wording uses `LLM` / real-model language instead of
  `Direct`; MCP tools are selected with a searchable collapsed multi-select;
  tool policy remains available only as an advanced governance fold; publish
  keeps version/API publishing as the primary path and folds evaluation/access
  governance controls.
- After 014.21, the preview header exposes a real debug icon action. Opening
  `调试详情` adds a fourth right-side column with `调用树` and `火焰图` views. The
  existing persona, orchestration, and preview columns must keep their current
  widths; the workbench uses horizontal scrolling for the expanded four-column
  state rather than squeezing the original columns.
- After 014.22, the orchestration header is intentionally plain and does not
  advertise default LLM/streaming mode as if it were an optional product mode.
  Runtime notices are visible only for actual precedence conflicts. Header icon
  buttons follow the Workflow/Chatflow canvas toolbar sizing and Element Plus
  icon system. Draft-only preview target selection is hidden until stable
  version targets exist.
- After 014.23, Workbench Preview's empty conversation state shows the saved
  opening message as the first assistant line. It does not restore the old
  assistant intro card. Suggested starters remain distinct from the opening
  message and are bottom-aligned in the preview conversation body.
- After 014.24, the opening message is rendered as an assistant bubble. Suggested
  starter bubbles are right-bottom aligned inside the preview conversation body
  and each bubble width fits its text with a max-width cap for long content. The
  preview composer is split into an upper message-input area and lower action
  toolbar without a middle divider; textarea manual resize is disabled; send
  and reset are icon-only controls, with reset beside the preview title and send
  right-aligned in the composer toolbar. User message bubbles in Workbench
  Preview and formal ChatView are light blue and content-width adaptive. The
  debug detail panel receives focus when opened and must avoid fabricated
  Coze-like metrics: it may display only data backed by the current preview run
  or explicit runtime configuration, such as session/run id, request time,
  first-response time, backend latency, finish reason, and input/output
  character counts.
- Section navigation is task-oriented but secondary after 014.17. It may be
  compact tabs, anchors, or a collapsible rail, but it must not replace the
  primary Coze-like persona column on desktop.
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
