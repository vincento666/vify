## Slice Notes

- Scope: lifecycle E2E contract repair for workflow/chatflow canvas UX.
- RED: `workflow-canvas-ux-lifecycle` previously timed out waiting for workflow output because the multi-condition workflow still used legacy `expression` routing and external/DNS-dependent API URLs.
- Updated the multi-condition workflow fixture to use Coze-like `conditionBranches` with semantic branch names and default branch metadata.
- Added a local `/text/...` API stub for API_CALL branches so lifecycle coverage does not depend on external DNS/network.
- Gates passed: workflow canvas lifecycle, workflow publish/open API/debug, chatflow publish/open shell, chatflow conversation run, full frontend unit, frontend build.
