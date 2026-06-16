# Plan 044: Frontend Ant Design Vue Migration

## Strategy

Use a direct final replacement with controlled incremental slices.

```text
Phase 1: Ant foundation
  package deps, app install, Ant CSS, optional locale/theme setup

Phase 2: cross-cutting direct replacements
  ElMessage, ElMessageBox, request feedback, shell icons

Phase 3: low-risk Modules
  provider, mcp, knowledge

Phase 4: medium-risk Modules
  chat, runtime-lab, agent workbench

Phase 5: high-risk Modules
  evaluation, workflow canvas

Phase 6: cleanup
  remove Element Plus, remove --el-* CSS, add import guard, full gates
```

## Target Dependency Shape

```json
{
  "dependencies": {
    "@ant-design/icons-vue": "...",
    "ant-design-vue": "...",
    "lucide-vue-next": "...",
    "vue": "...",
    "vue-router": "..."
  }
}
```

Element Plus stays only during migration slices. Final acceptance removes:

```text
element-plus
@element-plus/icons-vue
element-plus/dist/index.css
styles/element-override.css
```

`styles/element-override.css` is replaced by either:

```text
styles/ant-theme.css
project token CSS in styles/tokens.css
```

## Ant Install Module

Create one install seam:

```text
frontend/src/app/ant-design.ts
  installAntDesign(app)
  configure theme/locale/message/modal defaults
```

`main.ts` should only know:

```text
createApp(App)
  -> installAntDesign(app)
  -> router
```

## Direct Ant Usage Rule

```text
Feature pages and local components may import:
  ant-design-vue components
  ant-design-vue message
  ant-design-vue Modal
  @ant-design/icons-vue
  lucide-vue-next
```

Do not create a generic `shared/ui` adapter layer for 044. The host platform is
Ant Design Vue, so the lowest-cost integration path is direct Ant usage plus the
single app install seam. Existing exploratory `shared/ui` helpers should be
removed or bypassed during cleanup unless they have a separate product purpose.

## Component Mapping

```text
el-button        -> a-button
el-input         -> a-input / a-textarea
el-input-number  -> a-input-number
el-select        -> a-select
el-option        -> a-select-option or :options
el-switch        -> a-switch
el-dialog        -> a-modal
el-drawer        -> a-drawer
el-table         -> a-table
el-table-column  -> columns config or table slots
el-pagination    -> a-pagination or a-table pagination
el-empty         -> a-empty
el-tabs          -> a-tabs
el-tab-pane      -> a-tab-pane or items
el-tag           -> a-tag
el-tooltip       -> a-tooltip
el-avatar        -> a-avatar
el-upload        -> a-upload
el-steps         -> a-steps
ElMessage        -> message
ElMessageBox     -> Modal.confirm
```

## Risk Controls

### Import Guard

Add a test that fails on production usage:

```text
frontend/src/**/*
  must not contain:
    from 'element-plus'
    from "@element-plus/icons-vue"
    <el-
    --el-
    .el-
```

During migration, the guard can accept a shrinking allowlist per slice. Final
slice removes the allowlist.

### RED/GREEN Discipline

Each slice records:

```text
artifacts/slices/044-frontend-ant-design-vue-migration/{slice}/
├── red.txt
├── unit.txt
├── build.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

### Browser UAT

Required for:

- app shell navigation;
- provider table and form dialog;
- knowledge upload/import/export;
- chat conversation create/delete/send;
- runtime lab temporary model settings;
- agent workbench create/save/publish/preview;
- evaluation eval set/evaluator/experiment/report/compare;
- workflow canvas create/save/publish/test/debug.

### Visual And Rem Gate

Any app-owned CSS introduced or edited must use rem units. Run at least:

```text
rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
```

Final gate:

```text
rtk npm --prefix frontend run test:unit
rtk npm --prefix frontend run build
```

## Migration Order

Recommended order:

```text
044.0 inventory
044.1 Ant foundation
044.2 direct feedback/confirm/request replacement
044.3 direct table/form dialog replacement
044.4 app shell and icons
044.5 provider/mcp/knowledge
044.6 chat/runtime-lab/agent
044.7 evaluation
044.8 workflow
044.9 cleanup/import guard/docs
```

Workflow is last because it has the largest Element Plus surface and the most
custom CSS selectors against Element Plus internals.

## Current User-Scoped Checkpoint

This pass intentionally stops before workflow/chatflow migration. Under that
constraint, Element Plus remains temporarily installed and globally registered
for deferred workflow/chatflow pages only. All other migrated production modules
have focused Element Plus guards, browser UAT evidence, full unit, rem, and
build evidence under `artifacts/slices/044-frontend-ant-design-vue-migration/`.

## Rollback Plan

Before final cleanup, each migrated slice can be rolled back independently by
reverting its page or local component changes. After final cleanup, rollback
means restoring Element Plus dependencies and the previous slice implementation.

To avoid a large rollback blast radius:

- keep data contracts unchanged;
- preserve data-testid values;
- preserve routes;
- do not change backend APIs;
- do not refactor workflow business logic during UI migration.
