# Plan

1. Create SDD docs and evidence directory.
2. Copy or reference existing 071 RED failure evidence.
3. Run focused responsive canvas and rem governance tests.
4. Run full frontend unit tests.
5. Run production build.
6. Run browser phase UAT with screenshots and measurements.
7. Scan artifacts for secrets, update docs, and commit tracked SDD.

## Test Strategy

- Focused/rem:
  `npm --prefix frontend run test:unit -- src/views/workflow/workflowCanvasResponsiveLayout.test.ts src/views/workflow/workflowCanvasRemGovernance.test.ts src/remScaleClosure.test.ts`
- Full unit:
  `npm --prefix frontend run test:unit`
- Build:
  `npm --prefix frontend run build`
- Browser UAT:
  `node frontend/e2e/canvas-responsive-debug-dock-phases.mjs`
