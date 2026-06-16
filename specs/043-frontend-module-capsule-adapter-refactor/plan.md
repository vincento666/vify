# Plan 043: Frontend Module Capsule Adapter Refactor

## Architecture

```text
app/router.ts
  -> collect module routes

app/navigation.ts
  -> collect module nav items

modules/{module}/
  -> routes.ts
  -> nav.ts
  -> api.ts
  -> pages/
  -> model/

shared/resource/
  -> ports.ts
  -> hifyAdapters.ts
  -> registry.ts

shared/navigation/
  -> linkResolver.ts
```

The refactor deepens Module capsules by moving cross-Module knowledge into
shared interfaces and adapters. The goal is not to add a micro-frontend runtime;
the goal is to make the existing Vue 3 code movable by host menu Module.

## Refactor Strategy

### Step 1. Add shared seams without moving pages

Create:

```text
src/shared/api/request.ts
src/shared/host/request.ts
src/shared/resource/ports.ts
src/shared/resource/hifyAdapters.ts
src/shared/resource/registry.ts
src/shared/navigation/linkResolver.ts
src/shared/ui/
```

Keep compatibility exports from existing `src/api`, `src/host`, `src/utils`,
and `src/components/base` until all Modules migrate.

### Step 2. Add Module route/nav composition

Create Module exports:

```text
modules/provider/routes.ts
modules/provider/nav.ts
...
modules/runtime-lab/routes.ts
modules/runtime-lab/nav.ts
```

Then change app router/nav to aggregate these exports.

### Step 3. Move low-risk capsules

Move Provider, MCP, and Knowledge first because they are mostly self-contained.

```text
views/provider -> modules/provider/pages
views/mcp      -> modules/mcp/pages
views/knowledge -> modules/knowledge/pages
```

### Step 4. Keep Workflow as one capsule

Move all Workflow-owned pages/helpers together:

```text
views/workflow -> modules/workflow
```

Do not split Workflow, Chatflow, Canvas, API Resource, and Observe.

### Step 5. Split Chat and Runtime Lab

Move:

```text
views/chat/ChatView.vue -> modules/chat/pages
views/chat/UnifiedRoutingChatLab.vue -> modules/runtime-lab/pages
views/chat/unifiedRoutingChatLab.ts -> modules/runtime-lab/model
api/chat.ts -> modules/chat/api.ts
api/runtimeLab.ts -> modules/runtime-lab/api.ts
```

Chat uses `AgentCatalogPort` for runnable Agent options.
Runtime Lab uses shared link/resource adapters for Chatflow canvas/debug links.

### Step 6. Adapterize Agent

Agent replaces direct imports of raw cross-Module APIs with:

```text
ModelCatalogPort
KnowledgeCatalogPort
ToolCatalogPort
FlowCatalogPort
AgentPreviewPort
```

Default Hify adapters can call current internal APIs. Host adapters can replace
them through a registry/provider.

### Step 7. Adapterize Evaluation

Evaluation replaces direct imports of Agent/Workflow APIs with:

```text
EvaluationTargetCatalogPort
```

Evaluation report debug links come from `shared/navigation/linkResolver`.

## TDD Strategy

Add focused tests before moving each slice:

- route aggregation returns all existing paths;
- nav aggregation returns existing menu labels/order;
- module capsules do not import another module's private pages/model files;
- Agent adapters return the same data shape as current direct API calls;
- Evaluation target adapter returns same Agent/Workflow/Chatflow options;
- link resolver preserves existing Workflow/Chatflow/Knowledge/MCP paths.

## Frontend Gates

For each slice touching frontend visual files:

```bash
rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
rtk npm --prefix frontend run test:unit -- <focused tests>
```

Final gate:

```bash
rtk npm --prefix frontend run test:unit
rtk npm --prefix frontend run build
```

Browser UAT is required for any route/menu behavior change.

## Slice Plan

```text
043.1 shared seam foundation
043.2 router/nav aggregation
043.3 provider/mcp/knowledge capsules
043.4 workflow capsule move
043.5 chat/runtime-lab split
043.6 agent resource adapters
043.7 evaluation target adapters
043.8 import guard + final packaging docs
```

## Risks

- `WorkflowCreate.vue` is large and should move as a whole before deeper
  cleanup; do not rewrite canvas behavior inside this spec.
- Agent preview depends on Chat APIs; isolate through `AgentPreviewPort` before
  moving Agent pages.
- Evaluation target selection depends on Agent/Workflow APIs; isolate target
  catalog before moving panels.
- Host route prefixes may differ from Hify standalone paths; all cross-Module
  links must use a resolver seam.

## Non-Goals

- no backend contract changes;
- no workflow/chatflow split into separate host menu Modules;
- no micro-frontend runtime introduction;
- no feature redesign;
- no broad CSS/theme rewrite.
