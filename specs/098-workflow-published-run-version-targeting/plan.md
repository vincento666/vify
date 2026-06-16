# Implementation Plan: Workflow Published Run Version Targeting

## Slice 098.1 Target Published Run Version

1. Add RED backend integration tests for targeted workflow/chatflow published runs.
2. Add request schema field and service selection logic for optional `versionId`.
3. Preserve active-version behavior when `versionId` is absent.
4. Add frontend API optional `versionId` payload support.
5. Add a compact publish-dialog “run this version” action and status evidence.
6. Run backend, frontend/rem/build, and browser UAT gates.
7. Commit the focused feature point.

## Evidence Directory

`artifacts/slices/098-workflow-published-run-version-targeting/098.1/`
