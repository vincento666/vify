# Plan 014: Agent Workbench MVP

## Architecture

Implement the workbench as a frontend-first product upgrade over the existing
Agent, chat, provider, knowledge, workflow, and MCP APIs.

The MVP should avoid backend schema churn. New backend work should be limited to
small compatibility helpers only when existing APIs make the UX unnecessarily
fragile. The canonical Agent persistence remains:

- `agent.name`
- `agent.description`
- `agent.system_prompt`
- `agent.model_config_id`
- `agent.temperature`
- `agent.max_tokens`
- `agent.max_context_turns`
- `agent.knowledge_base_id`
- `agent.workflow_id`
- `agent_tool`

## Frontend Structure

Add a workbench feature area under `frontend/src/views/agent/`:

- `AgentWorkbench.vue`: route page and layout.
- `AgentWorkbenchShell.vue`: header, section navigation, responsive preview slot.
- `AgentCoreEditor.vue`: identity, model, instructions, generation settings.
- `AgentCapabilityPanel.vue`: capability cards and selectors.
- `AgentRuntimeSummary.vue`: mirrors backend mode precedence.
- `AgentPreviewPanel.vue`: saved-Agent chat preview using existing chat APIs.
- `agentWorkbench.ts`: form defaults, API adapters, mode summary helpers.
- Focused tests next to the workbench helpers/components.

The existing `AgentList.vue` should stay as the list entry. It may route create
and edit actions to the workbench instead of opening the old dialog once the
workbench is ready. During implementation, keep the modal path available until
the replacement passes gates.

## Routes

Add routes:

- `/agents/new`: create workbench.
- `/agents/:id/workbench`: edit workbench.

Keep `/agent` as the existing list route for compatibility with the current
sidebar and tests. A later cleanup may rename the list route after redirects and
tests are in place.

## Runtime Mode Summary

The frontend mode summary must mirror backend chat behavior:

1. `workflowId` present -> workflow mode.
2. Else `knowledgeBaseId` present -> RAG mode.
3. Else direct mode.
4. MCP tools currently participate only when the backend reaches the direct
   tool path.

The workbench should surface this as product language, for example:

- "Workflow mode: this workflow will run before the model answers."
- "RAG mode: the selected knowledge base will be searched before answering."
- "Direct mode with tools: the model may call bound MCP tools."
- "Tools are configured, but workflow mode currently takes priority."

## Preview Strategy

Use existing chat APIs:

1. Require saved Agent ID.
2. If form is dirty, ask the user to save before preview.
3. Create or reuse one preview chat session per open workbench instance.
4. Send preview messages through the existing SSE stream endpoint.
5. Reset deletes or abandons the local preview session and starts a fresh one.

Do not add a separate unsaved draft execution endpoint in the MVP.

## Backend Strategy

Backend changes should be conservative:

- Keep `/api/v1/agents` contracts unchanged.
- Keep `/api/v1/agents/{id}/tools` as full replacement.
- Reuse provider, knowledge, workflow, MCP list APIs for selectors.
- Add helper endpoints only if frontend would otherwise need duplicate fragile
  joins. Any helper must return the normal `{code, message, data}` envelope.

Potential helper, only if needed:

- `GET /api/v1/agents/{id}/workbench-options`: aggregated model, capability, and
  binding option metadata.

Prefer not to add it in the first pass unless tests show option loading is too
slow or error-prone.

## Testing Notes

- Unit tests cover form defaults, request mapping, dirty state, mode summary, and
  preview state transitions.
- Integration tests keep existing Agent and chat API contracts green.
- E2E tests cover route open, create/save, edit/save, bind capabilities, warning
  display, and preview streaming.
- Browser UAT must capture desktop and mobile screenshots.
- Preserve all existing spec 004 Agent tests before deleting or bypassing the old
  dialog behavior.

## Rollout Order

1. Build the route shell without changing the list modal behavior.
2. Implement core form load/save using existing endpoints.
3. Route `新增 Agent` and `编辑` from the list to the workbench.
4. Add capability cards.
5. Add runtime summary and warnings.
6. Add embedded preview.
7. Remove or retire the old modal only after equivalent UAT evidence exists.

## Out-of-Scope Implementation Notes

- Do not implement multi-Agent routing inside chat service for this spec.
- Do not add publish/channel routes.
- Do not add prompt optimization calls.
- Do not add new persistent memory or variable scopes.
- Do not embed Workflow/Chatflow canvas until 011/012 are production-ready.
