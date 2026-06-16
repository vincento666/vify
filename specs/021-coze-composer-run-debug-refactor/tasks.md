# Tasks 021: Coze Composer Run Debug Refactor

## 021.1 IA cleanup and route contract

- [x] RED: sidebar/navigation test fails while `观测` is still top-level.
- [x] Add route helper tests for Workflow, Chatflow, and Agent debug deep links.
- [x] Remove top-level Observe navigation from Coze composer product mode.
- [x] Keep compatibility route strategy documented for `/observe`.
- [x] Add E2E: sidebar has no Observe entry and existing Workflow/Chatflow/Agent entries remain.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 021.2 Workflow embedded run detail

- [x] RED: Workflow canvas deep-link E2E fails before implementation.
- [x] Add or adapt Workflow run debug endpoint/facade.
- [x] Load `runId`/`executeId` query params in Workflow canvas.
- [x] Auto-open bottom debug dock and select the requested run.
- [x] Render call tree, flamegraph/timeline, node input/output, raw payload, and errors in the dock.
- [x] Replace `/observe` navigation with in-canvas `查看运行详情`.
- [x] Add E2E: run Workflow, open deep link, verify selected run detail.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 021.3 Chatflow embedded run detail

- [x] RED: Chatflow canvas deep-link E2E fails before implementation.
- [x] Add or adapt Chatflow run debug endpoint/facade.
- [x] Load `runId`/`executeId` query params in Chatflow canvas.
- [x] Auto-open bottom debug dock and select requested run/session state.
- [x] Render conversation variables, channel/user identity, interrupt/resume events, call tree, flamegraph, node input/output, and errors.
- [x] Add E2E: interrupt/resume Chatflow, open deep link, verify event timeline and variables.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 021.4 Agent preview embedded run detail

- [x] RED: Agent Workbench preview deep-link test fails before implementation.
- [x] Add or adapt Agent preview run debug endpoint/facade.
- [x] Load `previewRunId&debug=1` query params in Agent Workbench.
- [x] Auto-open existing right debug detail panel and focus it.
- [x] Preserve four-column horizontal-scroll behavior without squeezing persona/orchestration/preview columns or header actions.
- [x] Render real preview-run data only: run ID, latency, finish reason, call tree/flamegraph, and input/output sizes.
- [x] Add E2E: preview run, reload deep link, verify panel and real data.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 021.5 Debug URL API compatibility

- [x] RED: Workflow/Chatflow API debug URL contract fails before implementation.
- [x] Make Workflow published/API execution return composer deep-link `debugUrl` / `debug_url`.
- [x] Make Chatflow published/API execution return composer deep-link `debugUrl` / `debug_url`.
- [x] Ensure debug URLs contain IDs only and do not leak raw input/output payloads.
- [x] Add integration tests for debug URL shape and ownership.
- [x] Add E2E: execute API, open returned debug URL, verify owning canvas opens debug panel.
- [x] Save Browser UAT screenshots.
- [x] Gates pass.

## 021.6 Retire standalone observe surface

- [x] RED: old `/observe` product-entry E2E captures the current duplicated behavior.
- [x] Remove or hide standalone Observe page from user-facing product mode.
- [x] Keep backend observe adapters only as internal data sources or compatibility endpoints.
- [x] Update debug dock links and labels from `查看观测详情` to composer-owned run detail wording.
- [x] Migrate E2E coverage from `/observe` page to Workflow/Chatflow/Agent embedded panels.
- [x] Add Browser UAT proving ordinary run debugging never leaves the owning composer surface.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.6/`.
- [x] Gates pass.

## 021.7 Canvas run/config polish regression

- [x] RED: toolbar zoom helper and config/node-test tests fail before the new affordances exist.
- [x] Make bottom toolbar zoom out/in buttons functional and add percentage preset menu for 25/50/75/100/125/150%.
- [x] Implement mouse/trackpad mode toggle from the original canvas spec.
- [x] Remove node-name editors from all node config schemas; START/END remain fixed labels.
- [x] Compact variable type labels to abbreviations only (`str.`, `num.`, `bool.`, `obj.`, `arr.`, `file.`).
- [x] Compact input/output parameter rows, remove duplicate input add button, and remove no-op output import/expand buttons.
- [x] Convert Chatflow stream output fields to switches.
- [x] Simplify Chatflow trial-run panel: no dataset/app shell, no JSON/AI/log no-op buttons, actual `开始试运行` action remains runnable.
- [x] Hide single-node test for START/END and remove no-op node action menu.
- [x] Remove bilingual composer header copy and force canvas textareas to `resize: none`.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.1-toolbar-controls/` through `021.4-visual-uat-polish/`.
- [x] Gates pass: full frontend unit, targeted backend integration, frontend build, Playwright E2E, and Browser UAT.

## 021.8 Chatflow trial chat panel and canvas control follow-up

- [x] RED: added failing canvas gesture helper tests and Chatflow trial-run e2e for chat window, collapsed runtime fields, no fit button, and no 500 responses.
- [x] Make trackpad mode use scroll panning with higher pan speed, keep mouse wheel zoom, and shorten programmatic zoom animation.
- [x] Remove the unused fit-view toolbar button.
- [x] Rework Chatflow trial-run into an Agent-like chat surface: collapsed runtime params, opening message, suggested questions, composer, user/assistant bubbles.
- [x] Align suggested questions with Agent preview behavior: trim/dedupe and click sends immediately.
- [x] Stop auto-opening the debug dock after Chatflow trial sends; load latest debug detail when users open the dock.
- [x] Add default Chatflow run integration guard for no 500 when END output is empty.
- [x] Fix publish gate dirty-state false positives after create-and-run route refresh.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.8-chatflow-trial-chat/`.
- [x] Gates pass: RED evidence, full frontend unit, backend integration, frontend build, focused Playwright E2E, and browser UAT.

## 021.9 Fixed START/END nodes and debug dock layout

- [x] RED: node config unit test fails while START exposes input-variable schema instead of output-variable schema.
- [x] RED: fixed-node E2E fails while START/END can be deleted with keyboard shortcuts.
- [x] RED: debug dock layout E2E fails while the dock overlaps the right-side config/trial panel.
- [x] Make START node show output variables and END node show input variables in canvas previews.
- [x] Disable VueFlow built-in delete key handling and prevent local canvas keyboard delete logic from removing START/END.
- [x] Keep END out of single-node output preview rows and START out of ordinary input preview rows.
- [x] Make the debug dock reserve horizontal space for right-side panels and node-test drawers.
- [x] Hide visible scrollbar chrome in the one-line Chatflow composer before wrapping is needed.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.9-fixed-nodes-layout/`.
- [x] Gates pass: RED evidence, full frontend unit, targeted backend integration, frontend build, focused Playwright E2E, and browser UAT.

## 021.10 Config collapse, END output, and debug errors panel polish

- [x] RED: node config unit test fails while END still exposes an `输入参数` section.
- [x] RED: debug errors E2E fails while switching `错误列表` changes the dock header title and lacks card-style error UI.
- [x] RED: config section E2E fails while section arrows are static text instead of real collapsible headers.
- [x] RED: END output E2E fails while END still exposes `输入参数` and `输出格式`.
- [x] Remove END node's standalone input-parameter section from the config schema.
- [x] Keep debug dock header title stable as `调试详情` across `错误列表` and `调试` tabs.
- [x] Render the error list as a Coze-like summary plus card/list empty state.
- [x] Make selected node config sections true buttons with `aria-expanded`, collapsible content, and rotating chevrons.
- [x] Hide `输出格式` only for END output variables while keeping the selector for ordinary output-producing nodes.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.10-config-collapse-errors-output/`.
- [x] Gates pass: RED evidence, full frontend unit, targeted backend integration, frontend build, focused Playwright E2E, and browser UAT.

## 021.11 Edge selection, deletion, and insert palette

- [x] RED: graph model unit test fails before selected edges can be deleted and split by inserted nodes.
- [x] RED: Chatflow edge E2E fails while hover has no plus insert button and selected edges cannot be deleted.
- [x] Add graph helpers to delete an edge and insert a node on an existing edge while reconnecting through the inserted node.
- [x] Render custom Coze canvas edges with hover and selected thick-highlight states.
- [x] Allow edge click selection and `Backspace`/`Delete` deletion without deleting START/END nodes.
- [x] Show a plus button at the edge midpoint while hovering or selecting an edge.
- [x] Open an edge-anchored node picker whose left edge aligns with the plus button center.
- [x] Insert the selected node at the edge midpoint and split the original edge into two edges.
- [x] Save evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.11-edge-interactions/`.
- [x] Gates pass: RED evidence, full frontend unit, targeted backend integration, frontend build, focused Playwright E2E, fixed-node deletion regression, and browser UAT.

## 021.12 Publish/Open API/debug IA regression

- [x] RED: canvas IA E2E fails while the header `观测` button opens the right-side `发布与运维 / 运行观测` panel and activates the unfinished `统计` tab.
- [x] RED: publish E2E fails while publish is only available as a right-side ops panel instead of a publish modal/dialog with version metadata.
- [x] Remove or hide the center `统计` tab from Workflow/Chatflow composer until a real statistics product is implemented.
- [x] Keep exactly one `开放` surface. Prefer the center `开放` tab as the full Open API/channel integration surface; remove the duplicated right-side ops-panel `Open API` tab.
- [x] Replace header `观测` behavior with a debug-dock toggle such as `调试详情` or `运行详情`, or remove the duplicate header action if the dock entry is already sufficient.
- [x] Remove the mixed `发布与运维` right-side panel. Its previous responsibilities split into publish modal, center `开放` tab, and bottom debug dock.
- [x] Remove `运行观测` from any ops panel/surface; trial/API/channel run details live in the existing bottom debug dock and deep-link through the 021 debug URL contract.
- [x] Replace the right-side publish tab/panel with a publish modal/dialog that contains publish checks, latest successful trial-run status, current draft/published state, version name/notes, confirm publish, and version history/rollback.
- [x] Keep publish checks in the publish modal only. The debug dock may show validation/runtime errors, but it must not duplicate publish confirmation or version-management controls.
- [x] Ensure legacy observe/open/publish routing no longer maps to `canvasTab = 'stats'`; no observe/debug action activates a statistics surface.
- [x] Add unit coverage for composer tab/ops/debug state transitions.
- [x] Add Playwright E2E for Workflow and Chatflow: the center `开放` tab opens the only Open API/channel surface, publish opens the modal, debug/observe opens the debug dock, and no duplicate ops/observe panel is rendered.
- [x] Add Browser UAT with screenshots under `artifacts/slices/021-coze-composer-run-debug-refactor/021.12-publish-open-debug-ia/`.
- [x] Gates pass: RED evidence, integration/contract regression, full frontend unit, frontend build, focused Playwright E2E, Browser UAT, and remScaleClosure if styles change.
