# Frontend Ant Design Vue Platform

Hify frontend uses Ant Design Vue as the host-aligned UI platform for migrated
production modules.

## App Seam

`frontend/src/app/ant-design.ts` is the single app install seam:

```text
installAntDesign(app)
  -> app.use(Antd)
  -> imports ant-design-vue/dist/reset.css once
  -> exports hifyAntTheme token bridge
```

`frontend/src/App.vue` mounts `a-config-provider` with `hifyAntTheme`, so Ant
components inherit Hify color, font, radius, and base sizing defaults.

## Feature Usage

Feature modules should import Ant Design Vue directly:

```text
ant-design-vue
@ant-design/icons-vue
lucide-vue-next
```

Use Ant primitives directly in pages and local components:

```text
message / Modal.confirm
a-button / a-input / a-select / a-switch
a-modal / a-drawer / a-upload
a-table / a-pagination
a-tabs / a-tag / a-tooltip / a-avatar
```

Do not add generic `shared/ui` UI-library wrappers for 044. That directory was
removed after migration because the intended integration model is direct Ant
usage plus the single app seam, not runtime UI-library switching.

## Current Boundary

Provider, MCP, Knowledge, Chat, Runtime Lab, Agent, Evaluation,
workflow/chatflow, base table/form dialog, app shell, feedback, confirm, request
feedback, and API Resource workbench are migrated to Ant.

Element Plus has been removed from production dependencies. Do not add
`element-plus`, `@element-plus/icons-vue`, `<el-*`, `.el-*`, or `--el-*` usage
back into production code.

## Gates

For visual frontend changes:

```bash
rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts
rtk npm --prefix frontend run test:unit
rtk npm --prefix frontend run build
```

For 044 migration slices, save RED/GREEN/UAT evidence under:

```text
artifacts/slices/044-frontend-ant-design-vue-migration/
```
