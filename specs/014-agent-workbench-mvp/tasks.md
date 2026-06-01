# Tasks 014: Agent Workbench

## 014.1 Workbench shell

- [ ] RED: route/UI smoke test fails for `/agents/new` and `/agents/:id/workbench`.
- [ ] Add workbench routes while preserving `/agent`.
- [ ] Implement shell header, section navigation, editor area, and preview area.
- [ ] Keep Agent list behavior unchanged until replacement gates pass.
- [ ] Gates pass.

## 014.2 Core configuration editor

- [ ] RED: workbench create/update form test fails.
- [ ] Implement Agent form defaults and detail-to-form adapter.
- [ ] Implement model option loading and grouped model selector.
- [ ] Implement identity, System Prompt, temperature, max tokens, and context-turn controls.
- [ ] Implement dirty state, save button state, and field-level validation.
- [ ] Verify create/update APIs remain source-compatible.
- [ ] Gates pass.

## 014.3 Capability cards

- [ ] RED: capability card persistence test fails.
- [ ] Implement MCP tool binding card with enabled server list and selected count.
- [ ] Implement knowledge base card with enabled KB selector and manage/open link.
- [ ] Implement workflow card with workflow selector and open link.
- [ ] Persist `toolIds`, `knowledgeBaseId`, and `workflowId`.
- [ ] Gates pass.

## 014.4 Runtime mode clarity

- [ ] RED: runtime summary and precedence warning tests fail.
- [ ] Implement frontend mode resolver mirroring backend precedence.
- [ ] Show direct/RAG/workflow mode badge and capability participation summary.
- [ ] Warn when tools are bound but workflow/RAG mode prevents direct tool path.
- [ ] Warn when both knowledge base and workflow are bound and workflow wins.
- [ ] Gates pass.

## 014.5 Embedded preview

- [ ] RED: preview chat flow test fails.
- [ ] Implement preview state machine: idle, creating session, streaming, done, error.
- [ ] Require save before preview when form is dirty or Agent is new.
- [ ] Send preview messages through existing chat SSE API.
- [ ] Implement reset preview session.
- [ ] Show runtime mode badge in the preview panel.
- [ ] Gates pass.

## 014.6 Validation and readiness polish

- [ ] RED: unsaved-change guard and backend-error UI tests fail.
- [ ] Implement leave guard for dirty form.
- [ ] Surface backend validation errors for missing/disabled model and unavailable MCP server.
- [ ] Add guided empty states for missing models, MCP servers, knowledge bases, and workflows.
- [ ] Verify desktop and mobile responsive layouts with browser screenshots.
- [ ] Update `uat.md` with create/edit/capability/preview evidence.
- [ ] Gates pass.

## 014.7 Chat entry polish

- [ ] RED: opening message and suggested-question UI tests fail.
- [ ] Add persisted opening message and suggested question fields.
- [ ] Show opening message in workbench preview and chat welcome state.
- [ ] Allow clicking a suggested question to send it as the next preview/chat message.
- [ ] Gates pass.

## 014.8 Version and release snapshots

- [ ] RED: Agent version snapshot contract test fails.
- [ ] Add additive Agent version storage and migrations.
- [ ] Snapshot all runtime-relevant Agent config into immutable versions.
- [ ] Add draft/latest/released selector in preview.
- [ ] Add release action with version diff summary.
- [ ] Gates pass.

## 014.9 Publish channels

- [ ] RED: publish shell API/UI tests fail.
- [ ] Add publish records and release-only publish guard.
- [ ] Add API/channel publish shells with status, endpoint/channel placeholder, and unpublish.
- [ ] Preserve real external channel adapters for later adapter-specific specs.
- [ ] Gates pass.

## 014.10 Memory and variables

- [ ] RED: variable and memory runtime tests fail.
- [ ] Add workbench-managed Agent variables with defaults and validation.
- [ ] Add durable single-Agent memory scopes.
- [ ] Inject variables and memory into chat prompt/runtime deterministically.
- [ ] Show preview controls for overriding variable values.
- [ ] Gates pass.

## 014.11 Prompt optimization

- [ ] RED: prompt optimizer UI/service tests fail.
- [ ] Add model-backed instruction draft/improve action.
- [ ] Show proposed diff and require explicit apply.
- [ ] Record prompt optimization audit metadata.
- [ ] Add cost/error/loading states.
- [ ] Gates pass.

## 014.12 Tool policy

- [ ] RED: tool policy contract and chat behavior tests fail.
- [ ] Persist durable per-tool policy after MCP tool metadata is available.
- [ ] Configure visibility, call mode, argument presets, approval, timeout, and failure behavior.
- [ ] Make chat tool runner honor policy.
- [ ] Show policy conflicts and unsupported tool metadata states in the workbench.
- [ ] Gates pass.

## 014.13 Knowledge retrieval settings

- [ ] RED: retrieval settings and RAG behavior tests fail.
- [ ] Add multi-knowledge-base selection.
- [ ] Add topK, score threshold, rerank option, and citation style settings.
- [ ] Make RAG search honor Agent retrieval settings.
- [ ] Show retrieval summary in preview responses.
- [ ] Gates pass.

## 014.14 Flow authoring link

- [ ] RED: linked Workflow/Chatflow authoring route tests fail.
- [ ] Add `打开画布` deep-link from Workflow/Chatflow capability cards to mature 011/012 full-page canvas routes.
- [ ] If an embedded mode is added, use full-screen/split authoring and preserve centered bottom toolbar, right config panel, ports, and bottom debug dock.
- [ ] Do not embed the canvas inside a small card or modal preview.
- [ ] Preserve workflow graph save/runtime contracts.
- [ ] Verify Agent workbench preview and capability cards still work after returning from the canvas.
- [ ] Gates pass.

## 014.15 Evaluation release gate

- [ ] RED: release gate blocks publish when selected evaluation fails.
- [ ] Link Agent versions to selected 013 experiments.
- [ ] Show latest run status, score, and failed-case count in release panel.
- [ ] Block release/publish when required gates fail.
- [ ] Allow rerun/open report actions through Evaluation routes.
- [ ] Gates pass.

## 014.16 Access, sharing, catalog, analytics

- [ ] RED: access/sharing/analytics shell tests fail.
- [ ] Add owner/access records and workbench access summary.
- [ ] Add share controls and catalog/marketplace visibility shell.
- [ ] Add usage, latency, error, evaluation, and release telemetry summaries.
- [ ] Add browser UAT evidence for admin shell and read-only states.
- [ ] Gates pass.
