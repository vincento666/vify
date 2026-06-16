# 071 Canvas Responsive Debug Dock

## Goal

Workflow and chatflow canvas pages must stay usable when the viewport narrows.
The layout should progressively shelve content instead of squeezing all panels
into the same visible area.

## Acceptance Criteria

- Preserve the current wide layout until the viewport crosses the responsive
  threshold.
- At the first constrained threshold, keep right-side detail panels fully
  visible and anchored to the viewport right edge.
- Shelve the right-side detail panels only at the next narrower threshold,
  leaving a small visible peek.
- At narrower widths, keep the left canvas rail usable and clip the stage
  horizontally instead of compressing it.
- At the narrowest widths, keep the left rail visible while the center stage is
  allowed to extend beyond the viewport.
- Keep the bottom debug dock fixed and stop shrinking it after its configured
  minimum width and height.
- Apply the same behavior to workflow and chatflow creation routes.
- Use `rem` units for newly added visual sizing.

## Evidence

- RED: `artifacts/slices/071-canvas-responsive-debug-dock/red-responsive.txt`
- RED for right-edge anchored regression:
  `artifacts/slices/071-canvas-responsive-debug-dock/red-right-anchored.txt`
- Unit and rem gates:
  `artifacts/slices/071-canvas-responsive-debug-dock/frontend-focused.txt`
- Unit and rem gates for right-edge anchored regression:
  `artifacts/slices/071-canvas-responsive-debug-dock/frontend-right-anchored-focused.txt`
- Full frontend unit:
  `artifacts/slices/071-canvas-responsive-debug-dock/frontend-unit.txt`
- Frontend build:
  `artifacts/slices/071-canvas-responsive-debug-dock/frontend-build.txt`
- Browser UAT:
  `artifacts/slices/071-canvas-responsive-debug-dock/uat.md`
