# Spec 026: Workflow/Chatflow Polish Hardening

## Goal

Make the current Workflow and Chatflow authoring surfaces feel production-ready:
layout must not overlap, list pages must be localized and visually consistent,
node config rows must stay aligned, section headers must be real collapses, and
variable reference controls must be lightweight and stable.

## Slices

1. **026.1 Layout alignment**: toolbar centers in the available canvas/debug area, debug dock avoids right panels, and trial-run panel bottom aligns with the debug dock.
2. **026.2 List polish**: Workflow and Chatflow list rows share the same table treatment, empty states, status labels, and Chinese button text.
3. **026.3 Shared controls**: introduce lightweight workflow icon-button/control styling and lucide-based action icons for non-critical controls.
4. **026.4 Config panel polish**: rename `输入参数` to `输入`, make bespoke LLM sections truly collapsible, widen config panels, and normalize row/control heights.
5. **026.5 Variable selector polish**: remove explicit reference/literal mode selection and replace broken popovers with a compact shared variable selector.

## Acceptance Gates

Every slice must save RED, unit, E2E, rem, and UAT evidence under
`artifacts/slices/026-workflow-chatflow-polish-hardening/{slice}/`.

Frontend visual changes must pass `remScaleClosure` and the full frontend unit
suite before final closeout.
