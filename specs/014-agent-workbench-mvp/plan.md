# Plan 014: Agent Workbench

## Architecture

Implement the workbench as a frontend-first product upgrade over the existing
Agent, chat, provider, knowledge, workflow, MCP, and evaluation APIs.

The first milestone should avoid backend schema churn. New backend work should
be limited to small compatibility helpers only when existing APIs make the UX
unnecessarily fragile. The canonical Agent persistence for the first milestone
remains:

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

Later milestones may add additive tables for Agent versions, publish records,
starter prompts, variables, memory, tool policy, retrieval settings, release
gates, access control, and telemetry. They must not break existing Agent CRUD or
chat contracts.

## Frontend Structure

Add a workbench feature area under `frontend/src/views/agent/`:

- `AgentWorkbench.vue`: route page and layout.
- `AgentWorkbenchShell.vue`: header, section navigation, responsive preview slot.
- `AgentPersonaColumn.vue`: Coze-like `人设与回复逻辑` authoring surface, prompt helper toolbar, and prompt template cards.
- `AgentOrchestrationColumn.vue`: Coze-like `编排` stack for model, skills, knowledge, memory, and conversation experience.
- `AgentPreviewDebugColumn.vue`: Coze-like `预览与调试` chat preview, process/log controls, and composer.
- `AgentCoreEditor.vue`: identity, model, instructions, generation settings.
- `AgentCapabilityPanel.vue`: capability cards, selectors, and deep links to linked Workflow/Chatflow canvas routes.
- `AgentRuntimeSummary.vue`: mirrors backend mode precedence.
- `AgentPreviewPanel.vue`: saved-Agent chat preview using existing chat APIs.
- `AgentStarterPanel.vue`: opening message and suggested questions.
- `AgentReleasePanel.vue`: versions, release state, publish targets, gates.
- `AgentMemoryVariablesPanel.vue`: single-Agent variables and memory scopes.
- `AgentToolPolicyPanel.vue`: per-tool policy once metadata is durable.
- `AgentKnowledgeSettingsPanel.vue`: retrieval settings and multi-KB selection.
- `AgentAnalyticsPanel.vue`: access, sharing, catalog, and metrics shell.
- `agentWorkbench.ts`: form defaults, API adapters, mode summary helpers.
- Focused tests next to the workbench helpers/components.

The existing `AgentList.vue` should stay as the list entry. It may route create
and edit actions to the workbench instead of opening the old dialog once the
workbench is ready. During implementation, keep the modal path available until
the replacement passes gates.

After 014.17, the desktop shell should be reorganized from the current
section-navigation-first layout to a Coze-aligned three-column layout:

1. Persona/reply logic column.
2. Orchestration column.
3. Preview/debug column.

The existing section keys can remain as internal state, mobile tabs, or compact
anchors, but they should no longer occupy the primary left column on desktop.

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
- "LLM mode with tools: the model may call bound MCP tools."
- "Tools are configured, but workflow mode currently takes priority."

## Preview Strategy

Use existing chat APIs:

1. Require saved Agent ID.
2. If form is dirty, ask the user to save before preview.
3. Create or reuse one preview chat session per open workbench instance.
4. Send preview messages through the existing SSE stream endpoint.
5. Reset deletes or abandons the local preview session and starts a fresh one.

Do not add a separate unsaved draft execution endpoint in the first milestone.

After versioning lands, preview can target draft, latest saved, or released
Agent versions. Until then, preview targets the saved draft Agent.

After 014.24, the preview UI treats chat entry as real conversation content:
the opening message is an assistant bubble, starter questions are right-bottom
aligned content-fit bubbles, user bubbles are light blue and content-fit, reset
is an icon beside the preview title, and the composer uses an upper textarea
plus lower icon action toolbar without a middle divider. Debug details focus
the panel on open and use only preview-run-backed data rather than fabricated
token/log metrics.

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

Later backend additions should be additive and module-local:

- Agent starter content: opening message and suggested questions.
- Agent version snapshots: immutable config copies for preview, evaluation, and
  publishing.
- Agent publish records: API/channel shell state and publish history.
- Agent memory and variables: scoped values used by single-Agent chat runtime.
- Agent tool policy: policy attached to durable MCP tool identifiers.
- Agent retrieval settings: multi-KB and retrieval behavior config.
- Agent release gates: links to Evaluation experiments/runs.
- Agent access/analytics: owner/access rows and usage/quality metrics.

Multi-Agent runtime tables, Agent-to-Agent links, and cross-Agent routing remain
out of scope.

## Testing Notes

- Unit tests cover form defaults, request mapping, dirty state, mode summary, and
  preview state transitions.
- Integration tests keep existing Agent and chat API contracts green.
- E2E tests cover route open, create/save, edit/save, bind capabilities, warning
  display, and preview streaming.
- Browser UAT must capture desktop and mobile screenshots.
- Preserve all existing spec 004 Agent tests before deleting or bypassing the old
  dialog behavior.
- Advanced slices must include migration/alembic tests when adding tables.
- Advanced runtime slices must include chat integration tests proving the new
  configuration is honored.

## Rollout Order

### Milestone 1: Authoring Loop

1. Build the route shell without changing the list modal behavior.
2. Implement core form load/save using existing endpoints.
3. Route `新增 Agent` and `编辑` from the list to the workbench.
4. Add capability cards.
5. Add runtime summary and warnings.
6. Add embedded preview.
7. Remove or retire the old modal only after equivalent UAT evidence exists.

### Milestone 2: Releaseable Agent

1. Add opening message and suggested questions.
2. Add Agent version snapshots and release state.
3. Add publish channel shells.
4. Add evaluation release gates.

### Milestone 3: Smarter Single-Agent Runtime

1. Add memory and variables.
2. Add prompt optimization with explicit approval.
3. Add fine-grained tool policy.
4. Add knowledge retrieval settings.
5. Add deep-linked or full-screen/split Workflow and Chatflow authoring after
   011/012 are stable.

### Milestone 4: Operations

1. Add owner/access and sharing controls.
2. Add catalog/marketplace shell for approved Agents.
3. Add usage, quality, and release telemetry.

### Milestone 5: Coze Detail Alignment

1. Reorganize the workbench into the observed Coze three-column desktop layout.
2. Move persona/reply logic into the left column with prompt helper actions and
   template cards.
3. Move model, skills, knowledge, memory, and conversation experience into the
   middle orchestration column.
4. Keep preview/debug always visible on the right.
5. Connect draft autosave, preview/test, version snapshot, release, publish, and
   observe/deep links into one visible lifecycle.
6. Preserve full-page Workflow/Chatflow canvas deep links rather than embedding
   flow canvases in the Agent detail page.

## Sequencing And Non-Scope Notes

- Do not implement multi-Agent routing inside chat service for this spec.
- Do not add Agent-to-Agent handoff, group chat, planner/worker teams, or
  cross-Agent routing.
- Sequence Workflow/Chatflow authoring links after 011/012 are production-ready. Prefer same-app deep links or full-screen/split authoring; do not place the canvas inside a small capability card or modal.
- Sequence external channel adapters after the publish shell and release/version
  contracts are stable.
