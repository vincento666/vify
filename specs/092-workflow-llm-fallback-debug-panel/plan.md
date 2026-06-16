# Plan 092

## 092.1 Fallback Evidence Formatter And Dock Rendering

- Add RED frontend coverage for formatting fallback attempts from
  `outputs.__debug.llm`.
- Add a small formatter in `workflowRunDebug.ts` with defensive redaction.
- Render the formatted fallback evidence in the selected workflow node detail
  panel.

## Gates

- RED focused frontend failure before implementation.
- Green focused workflow debug unit tests.
- Green rem gate because `WorkflowCreate.vue` is touched.
- Browser UAT through an existing workflow debug dock script or a focused script
  if the existing coverage cannot exercise the new evidence text.
