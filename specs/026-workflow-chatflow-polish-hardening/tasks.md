# Tasks 026: Workflow/Chatflow Polish Hardening

## 026.1 Layout alignment

- [x] RED: E2E fails while toolbar centers against the full canvas instead of the visible area.
- [x] RED: E2E fails while trial-run panel bottom differs from debug dock bottom.
- [x] Implement shared right-panel width/bottom variables for config, trial-run, node-test drawer, debug dock, and toolbar.
- [x] Unit/E2E/rem gates pass.
- [x] Browser UAT saved.

## 026.2 List polish

- [x] RED: list E2E fails while Chatflow has English labels and different row styling.
- [x] Align Workflow and Chatflow list pages with Chinese labels, status tags, action buttons, and empty states.
- [x] Unit/E2E/rem gates pass.
- [x] Browser UAT saved.

## 026.3 Shared controls

- [x] RED: control E2E/unit fails while icon controls use raw text symbols and inconsistent button surfaces.
- [x] Add lucide dependency and local workflow icon-button/control styling.
- [x] Replace non-critical configure/close/add/delete/more icons in Workflow/Chatflow canvas panels.
- [x] Unit/E2E/rem gates pass.
- [x] Browser UAT saved.

## 026.4 Config panel polish

- [x] RED: schema tests fail while `输入参数` titles remain.
- [x] RED: E2E fails while LLM model/skill headers are fake collapses.
- [x] Rename sections to `输入`, widen panels, and normalize input/output row heights.
- [x] Make LLM model/skill sections real collapsible headers with `aria-expanded`.
- [x] Unit/E2E/rem gates pass.
- [x] Browser UAT saved.

## 026.5 Variable selector polish

- [x] RED: E2E fails while value-mode dropdown and overflowed variable popover remain.
- [x] Add compact shared variable selector with direct literal input and link/chip picker.
- [x] Replace input, schema mapping, aggregation, assignment, and generic variable pickers.
- [x] Unit/E2E/rem gates pass.
- [x] Browser UAT saved.

## Final gate

- [x] Full frontend unit suite green.
- [x] Frontend build green.
- [x] Focused E2E suite green.
- [x] Browser UAT screenshots saved.
- [x] `spec.md`, `plan.md`, `tasks.md`, and `specs/README.md` updated.
