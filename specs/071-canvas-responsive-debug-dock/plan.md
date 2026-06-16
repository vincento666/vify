# 071 Plan

## Slice

Single frontend slice: responsive canvas shell and debug dock behavior shared by
workflow and chatflow routes.

## Design

- Add a pure responsive layout resolver that maps viewport width plus root `rem`
  to layout phases.
- Bind the phase class to `WorkflowCreate.vue`, which is the routed component
  for both workflow and chatflow canvas creation.
- Add CSS phase rules:
  - `canvas-layout-wide`
  - `canvas-layout-right-shelved`
  - `canvas-layout-stage-shelved`
  - `canvas-layout-left-rail`
- Keep right panels absolute and move them off-canvas before clipping the stage.
- Lock the debug dock to minimum `rem` dimensions once space is constrained.

## Subagent Split

- Investigator: locate routed canvas component, side panel rules, debug dock
  styles, and existing verification entry points.
- Test engineer: add RED coverage for progressive collapse and debug dock
  minimum sizing.
- Design reviewer: validate phase semantics and visual behavior against the
  requested Coze-like canvas pattern.

## Gates

- RED focused tests before implementation.
- Focused frontend unit plus `remScaleClosure`.
- Full frontend unit.
- Frontend build.
- Browser UAT for workflow and chatflow at four viewport phases.
