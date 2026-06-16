# Spec 043: Frontend Module Capsule Adapter Refactor

## Goal

Refactor the frontend architecture so each host menu module can be integrated as
a self-contained Module capsule while shared host, request, resource, link, and
UI seams stay reusable.

043 targets external host integration where the host system adds each Hify menu
Module separately instead of mounting the whole Hify frontend shell. The
frontend must therefore stop relying on a single global app shell, global route
table, and direct cross-Module API imports for module-level behavior.

## Context

The host frontend is not fully isomorphic with Hify. Its integration model is:

```text
host menu item
  -> one imported Hify Module capsule
  -> pages/assets/helpers colocated under that Module
  -> shared host/common components imported through public shared seams
```

Current Hify frontend is closer to:

```text
App.vue global shell
  -> appNavigation global menu
  -> router/index global route table
  -> views/* pages
  -> api/* global API facades
```

This works as a standalone product shell, but makes selective host integration
expensive because several menu Modules import other Module APIs or hard-code
routes outside their own area.

## Decisions

### D1. Workflow stays one Module capsule

Workflow is already a coherent product Module. Do not split Workflow, Chatflow,
Canvas, API Resource, and Observe into separate host Modules.

Target shape:

```text
modules/workflow/
├── routes.ts
├── nav.ts
├── api.ts
├── pages/
│   ├── WorkflowList.vue
│   ├── ChatflowList.vue
│   ├── WorkflowCreate.vue
│   ├── ApiResourceWorkbench.vue
│   ├── ObserveDashboard.vue
│   └── ObserveRedirect.vue
├── model/
└── widgets/
```

Workflow and Chatflow remain one host menu Module with two sub-module tabs.

### D2. Chat and Runtime Lab become separate Module capsules

`ChatView` and `UnifiedRoutingChatLab` must not live in the same Module capsule.

Target shape:

```text
modules/chat/
├── routes.ts
├── nav.ts
├── api.ts
├── pages/ChatView.vue
└── model/

modules/runtime-lab/
├── routes.ts
├── nav.ts
├── api.ts
├── pages/UnifiedRoutingChatLab.vue
└── model/
```

Runtime Lab may link to Chatflow canvas/debug through shared link adapters, not
by assuming the Workflow Module is present in the same route tree.

### D3. Agent uses shared adapters for cross-Module resources

Agent can depend on model, knowledge, tool, workflow/chatflow, and preview
capabilities, but it must not directly import those Modules' page files or raw
API facades.

Required interfaces:

```text
ModelCatalogPort
  getModelOptions()

KnowledgeCatalogPort
  listKnowledgeBases()
  resolveKnowledgeDocumentsLink(kbId)

ToolCatalogPort
  listMcpServers()
  resolveMcpManageLink()

FlowCatalogPort
  listWorkflows()
  listChatflows()
  resolveFlowCanvasLink(flow)

AgentPreviewPort
  createPreviewSession()
  streamPreviewMessage()
  deletePreviewSession()
```

Default adapters may call existing Hify APIs. Host adapters may call host APIs.

### D4. Evaluation uses shared adapters for target resources and evidence links

Evaluation can evaluate Agents, Workflows, and Chatflows, but it must depend on a
target catalog interface instead of importing Agent/Workflow API facades
directly.

Required interface:

```text
EvaluationTargetCatalogPort
  listAgentTargets()
  listWorkflowTargets()
  listChatflowTargets()
  resolveTargetDebugLink(target)
```

`EvaluationWorkbench` and child panels should call this interface through an
injected/default adapter.

### D5. Shared seams are real public interfaces

Shared code is allowed, but it must be explicit and small:

```text
shared/
├── api/request.ts
├── host/request.ts
├── ui/
├── resource/
│   ├── ports.ts
│   ├── hifyAdapters.ts
│   └── registry.ts
└── navigation/
    ├── ports.ts
    └── linkResolver.ts
```

Module capsules can import from `shared/*`, but must not import another
Module's private pages/model files.

## Scope

In scope:

- introduce `src/modules/*` Module capsule structure;
- introduce `src/shared/*` public seams;
- move Provider, MCP, Knowledge into low-risk capsules;
- keep Workflow as one capsule containing Workflow, Chatflow, Canvas, API
  Resource, and Observe;
- split Chat and Runtime Lab capsules;
- replace Agent direct cross-Module APIs with resource adapters;
- replace Evaluation direct target APIs and debug links with target adapters;
- convert global router/nav to aggregate Module `routes.ts` and `nav.ts`;
- preserve standalone Hify frontend behavior;
- keep host integration able to import one Module capsule without importing
  unrelated Module page files.

Out of scope:

- backend API changes;
- micro-frontend runtime framework;
- iframe-only integration;
- visual redesign;
- replacing Element Plus/Vue Router/Vite;
- splitting Workflow and Chatflow into separate host menu Modules;
- removing tests or rem governance.

## Target Module Layout

```text
frontend/src/
├── app/
│   ├── router.ts
│   ├── navigation.ts
│   └── shell/
├── shared/
│   ├── api/
│   ├── host/
│   ├── navigation/
│   ├── resource/
│   └── ui/
└── modules/
    ├── provider/
    ├── mcp/
    ├── knowledge/
    ├── workflow/
    ├── agent/
    ├── evaluation/
    ├── chat/
    └── runtime-lab/
```

## Capsule Rule

A Module capsule may import:

```text
its own files
shared/*
Vue/Vue Router/Element Plus/third-party libraries
```

A Module capsule must not import:

```text
modules/{other-module}/pages/*
modules/{other-module}/model/*
views/{other-module}/*
raw api facade from another Module after adapters exist
hard-coded route paths owned by another Module
```

Cross-Module behavior must go through a shared interface and adapter.

## Acceptance Criteria

- global router is composed from Module route exports;
- global navigation is composed from Module nav exports;
- Provider, MCP, Knowledge modules can be copied with only `shared/*` and still
  compile;
- Workflow capsule contains Workflow, Chatflow, Canvas, API Resource, and
  Observe pages;
- Chat and Runtime Lab have separate routes/nav/api/model folders;
- Agent no longer imports raw `knowledge`, `mcp`, `workflow`, or `chat` API
  facades directly; it uses resource/preview adapters;
- Evaluation no longer imports raw `agent` or `workflow` API facades directly;
  it uses target catalog adapters;
- cross-module links are produced by `shared/navigation/linkResolver`;
- no Module imports another Module's private page/model files;
- standalone Hify frontend route behavior stays compatible;
- frontend rem gate remains green;
- focused unit tests cover module route aggregation and adapter contracts.

## Completion Capability

After 043, the host frontend can integrate individual Hify menu Modules as
capsules. Each Module can be placed under the host's own menu route and can use
host-provided adapters for resource catalogs, links, permissions, and request
context.

## Specification Sign-off

Status: ready for implementation planning.

043 is an architecture refactor spec. It must preserve current user-facing
behavior while changing where Module interfaces live.
