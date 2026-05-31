# Tasks 014: Agent Workbench MVP

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
