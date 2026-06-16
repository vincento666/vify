# Spec 044: Frontend Ant Design Vue Migration

## Goal

Replace the frontend production UI library from Element Plus to Ant Design Vue
while preserving existing product behavior, module integration capability, rem
governance, and host integration seams.

This spec follows 043. Where 043 makes frontend Modules more self-contained,
044 removes the Element Plus dependency and aligns the frontend with the host
system's Ant Design Vue UI platform. Because the host is already standardized
on Ant Design Vue, this migration intentionally avoids a UI-library-agnostic
adapter layer.

## Direct Replacement Decision

Final state:

```text
frontend production runtime
  uses ant-design-vue
  uses @ant-design/icons-vue or lucide-vue-next
  does not import element-plus
  does not register ElementPlus globally
  does not render el-* component tags
  does not depend on --el-* design tokens in app-owned CSS
```

Implementation may be incremental, but every slice must either:

- replace an Element Plus dependency with Ant Design Vue directly; or
- move global installation, CSS, locale, and theme setup into
  `frontend/src/app/ant-design.ts`.

Runtime switching between Element Plus and Ant Design Vue is out of scope.
Generic `shared/ui` wrappers are also out of scope for this migration. Product
Modules may import and use Ant Design Vue components, composables, `message`,
and `Modal` APIs directly.

## Current Friction

Current shape:

```text
main.ts
  -> ElementPlus global plugin
  -> Element Plus icons global registry
  -> element-plus/dist/index.css

views/*
  -> el-button / el-input / el-select / el-table / el-dialog
  -> ElMessage / ElMessageBox
  -> @element-plus/icons-vue
  -> CSS overrides using --el-* tokens and .el-* internals
```

This creates integration friction because the host shell expects Ant Design Vue
runtime conventions while this project still installs and renders Element Plus.
The target is a direct Ant Design Vue runtime, not a library-neutral UI
abstraction.

Target shape:

```text
frontend/src/
├── app/
│   └── ant-design.ts
├── main.ts
│   └── installAntDesign(app)
└── views/ and feature Modules
    └── use Ant Design Vue directly
```

## Scope

In scope:

- add Ant Design Vue and Ant Design Vue icons;
- remove Element Plus and Element Plus icons from production dependencies;
- replace global Element Plus installation with Ant Design Vue installation;
- migrate message, confirm, request error feedback, table, form dialog, modal,
  drawer, select, input, switch, upload, tabs, tag, steps, tooltip, avatar, and
  icon usage;
- replace `--el-*` and `.el-*` app-owned CSS assumptions with project tokens,
  Ant Design Vue tokens, or app-owned class names;
- preserve existing route behavior, module behavior, data-testid hooks, API
  calls, and response handling;
- add import guards preventing new `element-plus` usage after migrated slices;
- run full acceptance on high-risk components and flows;
- keep frontend rem governance green for all app-owned CSS changes.

Out of scope:

- visual redesign;
- backend API changes;
- replacing Vue, Vite, Vue Router, or Vue Flow;
- runtime UI library switching;
- UI-library-agnostic adapter/wrapper design;
- creating broad `shared/ui` component wrappers such as `HButton`, `HInput`,
  `HSelect`, `HTable`, `HFormDialog`, or `HUpload` for the purpose of future UI
  library replacement;
- rewriting workflow canvas business logic;
- changing host integration contracts from 043.

## Ant Platform Seam

```text
frontend/src/app/ant-design.ts
  installAntDesign(app)
  import ant-design-vue/dist/reset.css once
  configure Ant Design Vue global plugin
  optionally configure locale/theme tokens when needed by the host
```

This is the only required UI seam in 044. All feature pages may migrate directly
to Ant Design Vue:

```text
ElMessage        -> message
ElMessageBox     -> Modal.confirm
el-popconfirm    -> a-popconfirm
el-table         -> a-table
el-form          -> a-form
el-dialog        -> a-modal
el-upload        -> a-upload
```

If exploratory `shared/ui` helpers already exist, they are not the target
architecture for 044 and should be removed or bypassed before final acceptance
unless they serve a separate non-UI-library-abstraction purpose.

## High-Risk Components

These areas require full acceptance because Ant Design Vue semantics differ
from Element Plus:

```text
message / confirm
  ElMessage, ElMessageBox -> message, Modal.confirm
  risk: promise behavior, cancellation, global container, z-index

form / validation
  el-form -> a-form
  risk: validate API, rules shape, label layout, error timing

table / pagination
  el-table -> a-table
  risk: column slots, fixed columns, row key, empty state, pagination event shape

select / option groups
  el-select -> a-select
  risk: filter behavior, clear behavior, grouped options, model value type

modal / drawer
  el-dialog / el-drawer -> a-modal / a-drawer
  risk: v-model prop name, footer slots, destroy behavior, focus trap

upload
  el-upload -> a-upload
  risk: beforeUpload return contract, file object shape, manual upload flow

workflow canvas controls
  risk: canvas keyboard handling, inline variable popovers, config panel layout

evaluation workbench
  risk: dense tables, tabs, dialogs, CSV import, report drilldown
```

## Acceptance Criteria

Current checkpoint: the user requested not to advance workflow/chatflow yet.
Therefore the final dependency-removal criteria below remain pending until the
workflow/chatflow slice is allowed. This checkpoint completes all other
production modules with Ant Design Vue migration, focused tests, rem gate, full
frontend unit gate, build gate, and browser UAT.

- `frontend/package.json` contains `ant-design-vue` and no `element-plus`
  production dependency.
- `frontend/src/main.ts` installs Ant Design Vue and does not install
  Element Plus.
- No production file under `frontend/src` imports `element-plus` or
  `@element-plus/icons-vue`.
- No production Vue template under `frontend/src` renders `<el-*` tags.
- No app-owned CSS under `frontend/src` relies on `.el-*` selectors or
  `--el-*` variables.
- `request.ts`, `notify.ts`, and `useConfirm.ts` no longer import Element Plus;
  they may use Ant Design Vue `message`/`Modal` directly or be removed if no
  longer needed.
- Tables render through Ant Design Vue `a-table` directly or through existing
  local components that are Ant-only and not UI-library-agnostic wrappers.
- Form dialogs render through Ant Design Vue `a-modal`/`a-form` directly or
  through existing local components that are Ant-only and not UI-library-
  agnostic wrappers.
- No production caller depends on `shared/ui` as the migration abstraction seam.
- Provider, MCP, Knowledge, Chat, Runtime Lab, Agent, Evaluation, and Workflow
  routes stay compatible.
- Workflow canvas create/save/publish/debug flows pass focused tests and
  browser UAT.
- Evaluation eval-set/evaluator/experiment/report/compare flows pass focused
  tests and browser UAT.
- `frontend/src/remScaleClosure.test.ts` passes after visual changes.
- Full frontend unit tests pass.
- Frontend build passes.
- Evidence is saved under
  `artifacts/slices/044-frontend-ant-design-vue-migration/`.

## Completion Capability

After 044, frontend Modules can be integrated into a host system without
forcing the host to accept Element Plus as a runtime dependency. The frontend
uses the host-aligned Ant Design Vue platform directly, while global Ant
installation details remain centralized in `app/ant-design.ts`.
