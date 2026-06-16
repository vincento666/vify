# Tasks 014: Agent Workbench

## 014.1 Workbench shell

- [x] RED: route/UI smoke test fails for `/agents/new` and `/agents/:id/workbench`.
- [x] Add workbench routes while preserving `/agent`.
- [x] Implement shell header, section navigation, editor area, and preview area.
- [x] Keep Agent list behavior unchanged until replacement gates pass.
- [x] After replacement gates passed, route Agent list `新增 Agent` and `编辑` to full-page workbench pages instead of the legacy dialog.
- [x] Gates pass.

## 014.2 Core configuration editor

- [x] RED: workbench create/update form test fails.
- [x] Implement Agent form defaults and detail-to-form adapter.
- [x] Implement model option loading and grouped model selector.
- [x] Implement identity, System Prompt, temperature, max tokens, and context-turn controls.
- [x] Implement dirty state, save button state, and field-level validation.
- [x] Verify create/update APIs remain source-compatible.
- [x] Gates pass.

## 014.3 Capability cards

- [x] RED: capability card persistence test fails.
- [x] Implement MCP tool binding card with enabled server list and selected count.
- [x] Implement knowledge base card with enabled KB selector and manage/open link.
- [x] Implement workflow card with workflow selector and open link.
- [x] Persist `toolIds`, `knowledgeBaseId`, and `workflowId`.
- [x] Gates pass.

## 014.4 Runtime mode clarity

- [x] RED: runtime summary and precedence warning tests fail.
- [x] Implement frontend mode resolver mirroring backend precedence.
- [x] Show direct/RAG/workflow mode badge and capability participation summary.
- [x] Warn when tools are bound but workflow/RAG mode prevents the LLM tool-call path.
- [x] Warn when both knowledge base and workflow are bound and workflow wins.
- [x] Gates pass.

## 014.5 Embedded preview

- [x] RED: preview chat flow test fails.
- [x] Implement preview state machine: idle, creating session, streaming, done, error.
- [x] Require save before preview when form is dirty or Agent is new.
- [x] Send preview messages through existing chat SSE API.
- [x] Implement reset preview session.
- [x] Show runtime mode badge in the preview panel.
- [x] Gates pass.

## 014.6 Validation and readiness polish

- [x] RED: unsaved-change guard and backend-error UI tests fail.
- [x] Implement leave guard for dirty form.
- [x] Surface backend validation errors for missing/disabled model and unavailable MCP server.
- [x] Add guided empty states for missing models, MCP servers, knowledge bases, and workflows.
- [x] Verify desktop and mobile responsive layouts with browser screenshots.
- [x] Update `uat.md` with create/edit/capability/preview evidence.
- [x] Gates pass.

## 014.7 Chat entry polish

- [x] RED: opening message and suggested-question schema, CRUD, and UI tests fail.
- [x] Add persisted opening message and suggested question fields.
- [x] Add additive baseline schema, Alembic migration, and existing-database compatibility columns.
- [x] Show opening message in workbench preview and chat welcome state.
- [x] Allow clicking a suggested question to send it as the next preview/chat message.
- [x] Verify Workbench preview and ChatView suggested-question clicks use a real OpenRouter LLM provider, not mock models.
- [x] Record current boundary: suggested questions are static first-turn starters; future per-turn `智能推荐` must be a separate LLM-backed toggle and not replace the opening message.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.7-chat-entry-polish/`.
- [x] Gates pass.

## 014.8 Version and release snapshots

- [x] RED: Agent version snapshot contract test fails.
- [x] Add additive Agent version storage and migrations.
- [x] Snapshot all runtime-relevant Agent config into immutable versions.
- [x] Add draft/latest/released selector in preview.
- [x] Add release action with version status summary.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.8-version-release-snapshots/`.
- [x] Gates pass.

## 014.9 Publish channels

- [x] RED: publish shell API/UI tests fail.
- [x] Add publish records and release-only publish guard.
- [x] Add API/channel publish shells with status, endpoint/channel placeholder, and unpublish.
- [x] Preserve real external channel adapters for later adapter-specific specs.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.9-publish-channels/`.
- [x] Gates pass.

## 014.10 Memory and variables

- [x] RED: variable and memory runtime tests fail.
- [x] Add workbench-managed Agent variables with defaults and validation.
- [x] Add durable single-Agent memory scopes.
- [x] Inject variables and memory into chat prompt/runtime deterministically.
- [x] Show preview controls for overriding variable values.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.10-memory-variables/`.
- [x] Gates pass.

## 014.11 Prompt optimization

- [x] RED: prompt optimizer UI/service tests fail.
- [x] Add model-backed instruction draft/improve action.
- [x] Show proposed diff and require explicit apply.
- [x] Record prompt optimization audit metadata.
- [x] Add cost/error/loading states.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.11-prompt-optimization/`.
- [x] Gates pass.

## 014.12 Tool policy

- [x] RED: tool policy contract and chat behavior tests fail.
- [x] Persist durable per-tool policy after MCP tool metadata is available.
- [x] Configure visibility, call mode, argument presets, approval, timeout, and failure behavior.
- [x] Make chat tool runner honor policy.
- [x] Show policy conflicts and unsupported tool metadata states in the workbench.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.12-tool-policy/`.
- [x] Gates pass.

## 014.13 Knowledge retrieval settings

- [x] RED: retrieval settings and RAG behavior tests fail.
- [x] Add multi-knowledge-base selection.
- [x] Add topK, score threshold, rerank option, and citation style settings.
- [x] Make RAG search honor Agent retrieval settings.
- [x] Show retrieval summary in preview responses.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.13-knowledge-retrieval-settings/`.
- [x] Gates pass.

## 014.14 Flow authoring link

- [x] RED: linked Workflow/Chatflow authoring route tests fail.
- [x] Add `打开画布` deep-link from Workflow/Chatflow capability cards to mature 011/012 full-page canvas routes.
- [x] If an embedded mode is added, use full-screen/split authoring and preserve centered bottom toolbar, right config panel, ports, and bottom debug dock.
- [x] Do not embed the canvas inside a small card or modal preview.
- [x] Preserve workflow graph save/runtime contracts.
- [x] Verify Agent workbench preview and capability cards still work after returning from the canvas.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.14-flow-authoring-link/`.
- [x] Gates pass.

## 014.15 Evaluation release gate

- [x] RED: release gate blocks publish when selected evaluation fails.
- [x] Link Agent versions to selected 013 experiments.
- [x] Show latest run status, score, and failed-case count in release panel.
- [x] Block release/publish when required gates fail.
- [x] Allow rerun/open report actions through Evaluation routes.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.15-evaluation-release-gate/`.
- [x] Gates pass.

## 014.16 Access, sharing, catalog, analytics

- [x] RED: access/sharing/analytics shell tests fail.
- [x] Add owner/access records and workbench access summary.
- [x] Add share controls and catalog/marketplace visibility shell.
- [x] Add usage, latency, error, evaluation, and release telemetry summaries.
- [x] Add browser UAT evidence for admin shell and read-only states.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.16-access-sharing-analytics/`.
- [x] Gates pass.

## 014.list Agent homepage layout polish

- [x] RED: Agent list layout and timestamp tests fail.
- [x] Keep `/agent` as the Agent module homepage/list entry.
- [x] Keep create/edit entry routed to full-page workbench.
- [x] Stabilize list row height when Agent names and model names are long.
- [x] Format created time as compact minute precision text.
- [x] Verify action column width, no horizontal overflow, and browser UAT screenshot.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.18-agent-list-homepage-polish/`.
- [x] Gates pass.

## 014.17 Coze three-column lifecycle alignment

- [x] RED: Coze-aligned Agent detail layout and lifecycle tests fail.
- [x] Preserve the Agent list entry, existing Agent CRUD contracts, and current preview chat contracts.
- [x] Reorganize desktop workbench into three primary columns:
  - left `人设与回复逻辑`: Agent name/persona prompt, reply logic, helper toolbar, prompt template cards, opening/suggested-question entry points where appropriate.
  - middle `编排`: model settings, skills/plugins, workflow/chatflow binding, knowledge text/table/photo shells, variables, database/memory/file-box shells, conversation experience controls.
  - right `预览与调试`: chat preview, process/log/config controls, draft/latest/released target selector, composer, generated-content disclaimer, and trace/debug entry points.
- [x] Move current section navigation into compact tabs, anchors, or mobile-only navigation so it does not replace the persona column on desktop.
- [x] Add Coze-like header state: back, avatar/name/edit, Agent mode selector, autosave timestamp, utility action, and primary publish.
- [x] Implement draft autosave visual state or a spec-backed placeholder if true autosave is deferred.
- [x] Connect lifecycle actions visibly: configure persona -> configure orchestration -> preview/debug -> create version -> release -> publish.
- [x] Keep Workflow/Chatflow capability actions as full-page canvas deep links; do not embed the flow canvas inside the Agent detail page.
- [x] Browser UAT must compare against `artifacts/research/coze-agent-detail/spec-014-live-audit-20260602.md` screenshots.
- [x] Save evidence under `artifacts/slices/014-agent-workbench-mvp/014.17-coze-three-column-lifecycle/`.
- [x] Gates pass.

## 014.19 Agent detail MVP trim and real-provider direct mode

- [x] RED: current Agent detail still exposed top anchor tabs, persona name/description/template shells, publish/access blocks inside orchestration, and preview shell buttons.
- [x] Remove desktop anchor tabs above the three-column workbench.
- [x] Move Agent name editing into the header and keep the left persona column as pure System Prompt / reply logic for the current MVP.
- [x] Remove non-MVP recommendation/template cards and equalize persona/orchestration/preview column heights.
- [x] Keep orchestration modules collapsible and limited to current MVP: model settings, conversation experience, memory, and skills/knowledge/workflow.
- [x] Move `版本与发布`, `发布渠道`, `访问与分享`, and analytics into the `发布` lifecycle dialog.
- [x] Remove preview/debug header buttons that do not have functional behavior.
- [x] Filter mock model providers from the Agent model selector and bind the browser UAT Agent to OpenRouter `xiaomi/mimo-v2-flash`.
- [x] Keep Workflow/Chatflow actions as full-page canvas deep links.
- [x] Make disabled MCP tool policy survive the real LLM tool-call path without executing the MCP tool result.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.19-agent-detail-mvp-trim/`.
- [x] Gates pass.

## 014.20 Agent detail usability trim

- [x] RED: browser UAT showed persona textarea width issues, preview empty state looked like a bordered assistant card, `Direct` wording was ambiguous, MCP tool list over-expanded the page, and release dialog still exposed non-primary governance settings too prominently.
- [x] Force the persona System Prompt editor to fill the left column width.
- [x] Remove border/background from preview empty assistant introduction while preserving real chat message bubbles.
- [x] Rename `Direct` runtime wording to `LLM` / real-model language so it is not confused with echo/mock behavior.
- [x] Replace MCP Server checkbox list with a searchable collapsed multi-select.
- [x] Keep tool policy as an advanced folded governance section because it is useful for Hify safety/runtime control but not a Coze base-column item.
- [x] Trim publish dialog to the primary flow: create/release version and publish API; keep evaluation gate and access/sharing/analytics as folded advanced controls.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.20-agent-detail-usability-trim/`.
- [x] Gates pass.

## 014.21 Preview debug detail panel

- [x] RED: Coze lifecycle E2E failed because the debug detail panel squeezed the existing persona/orchestration/preview columns and did not expose horizontal scrolling.
- [x] Remove non-functional floating publish summary tags such as collapsed `关闭` / `PRIVATE` pills from the release dialog.
- [x] Remove the preview empty-state assistant introduction card; keep first-turn suggested questions and saved Agent preview behavior.
- [x] Replace preview header shell controls with a functional debug icon button.
- [x] Add a right-side `调试详情` panel with core `调用树` and `火焰图` tabs, run summary, Logid, and node detail.
- [x] Lock the existing three-column widths before opening debug detail, add the fourth column to the right, and expose horizontal scrolling instead of squeezing existing columns.
- [x] Verify with browser UAT and E2E that preview/debug, publish, and production build gates pass.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.21-preview-debug-detail-panel/`.
- [x] Gates pass.

## 014.22 Agent configuration effective UAT

- [x] RED: Coze lifecycle E2E failed while the orchestration header still showed capability/runtime pills and the preview header exposed a Draft-only selector with oversized debug button styling.
- [x] Align Agent Workbench icon buttons with the Workflow/Chatflow canvas toolbar icon system: compact Element Plus icon buttons, no raw character buttons.
- [x] Keep the orchestration header as a plain `编排` title; do not show default LLM/streaming mode as a visible product choice.
- [x] Show runtime priority notices only when bindings create an actual precedence/conflict warning.
- [x] Hide the preview target selector until there is more than one real preview target.
- [x] Force orchestration module titles and descriptions onto separate visual lines.
- [x] Verify persona and orchestration configuration effectiveness, including UI persistence, real LLM preview, memory/variables injection, chat-entry starters, version preview, capabilities, retrieval settings, tool policy, prompt optimization, and flow links.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.22-agent-configuration-effective-uat/`.
- [x] Gates pass.

## 014.23 Preview opening message and bottom starters

- [x] RED: Workbench Preview chat-entry E2E failed because the configured opening message was not visible as the first assistant message before chatting.
- [x] Render the configured opening message as the first assistant line in the preview conversation empty state without restoring the old assistant intro card.
- [x] Keep `猜你想问` separate from the opening message and align starter questions to the bottom of the preview conversation body.
- [x] Preserve suggested-question click behavior through the real non-mock LLM preview path and formal ChatView path.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.23-opening-message-preview-bottom-suggestions/`.
- [x] Gates pass.

## 014.24 MCP/RAG runtime proof and preview composer polish

- [x] RED: Agent tool-policy E2E failed when provider discovery only checked the first page of many mock providers; preview chat-entry visual assertions were extended to catch right-bottom starter alignment, assistant opening bubble styling, adaptive bubble widths, composer toolbar structure, disabled textarea resize, and icon-only send/reset controls.
- [x] Prove MCP tool policy is runtime-effective, not a shell: disabled tool policy blocks the MCP tool result through the chat path.
- [x] Prove knowledge recall uses real vector retrieval plus keyword/FAQ matching by merging keyword-ranked chunks into vector search results.
- [x] Render Workbench Preview opening copy as an assistant message bubble.
- [x] Align `猜你想问` starter bubbles to the right-bottom of the preview conversation body, with each bubble width fitting its text and long text capped by max width.
- [x] Convert preview composer to top textarea + bottom action toolbar without a middle divider, disable manual textarea resize, use icon-only send, and move reset to the preview header as an icon button.
- [x] Keep user message bubbles light blue and width-adaptive in Workbench Preview and formal ChatView.
- [x] Focus the debug detail panel when opened and show only data backed by a real preview run: preview session RunID, request time, first-response time, backend latency, finish reason, input/output character counts, and actual user/LLM call nodes.
- [x] Evidence: `artifacts/slices/014-agent-workbench-mvp/014.24-mcp-rag-chat-bubble-polish/`.
- [x] Gates pass.
