# Tasks 027: Workflow/Chatflow Config Hardening

## 027.1 Start defaults and trial input

- [x] RED: unit/E2E fails while default Start variables are deletable/required.
- [x] Mark runtime default Start variables as built-in and force `required=false`.
- [x] Disable editing, required toggle, and delete for built-in Start rows.
- [x] Ensure trial runs do not ask for built-in message/runtime variables.
- [x] Unit/E2E/rem/build/UAT gates pass.

## 027.2 Variable reference controls

- [x] RED: E2E fails while legacy variable buttons remain.
- [x] Replace remaining variable buttons with inline `{` trigger and compact picker.
- [x] Unit/E2E/rem/build/UAT gates pass.

## 027.3 Floating selectors

- [x] RED: E2E fails while model/dropdown picker reflows panel content.
- [x] Render model/resource/select menus as floating overlays.
- [x] Unit/E2E/rem/build/UAT gates pass.

## 027.4 Selector branch conditions

- [x] RED: integration/E2E fails while branch condition rows lack variable/default support.
- [x] Update schema normalization and runtime condition evaluation.
- [x] Align add-branch/add-condition button layout.
- [x] Unit/integration/E2E/rem/build/UAT gates pass.

## 027.5 Icon button final polish

- [x] RED: visual/E2E fails while icon buttons diverge.
- [x] Apply final shared icon-button styles.
- [x] Full final gates pass.

## Final gate

- [x] Full frontend unit suite green.
- [x] Frontend build green.
- [x] Frontend rem gate green.
- [x] Workflow/chatflow backend integration green.
- [x] Focused E2E suite green for Start defaults, inline variable trigger, floating selectors, condition branches, variable selector polish, config panel polish, and icon button polish.
- [x] Browser UAT screenshots saved for condition branch picker and icon button polish.

## 027.6 Config panel zoom and edge insert regression

- [x] RED: right config panel still resizes/refits canvas and changes visual scale.
- [x] Remove config-panel state from canvas layout refit watcher and stop shrinking `.coze-flow` for `has-right-panel`.
- [x] Move edge insert palette away from the plus button and above its stacking layer.
- [x] Evidence: `artifacts/slices/083-workflow-chatflow-canvas-node-parity/`.
- [x] Gates pass.
