# Spec 011-012 Node Interaction Correction UAT Report

Date: 2026-06-01

## Scope

- Workflow and Chatflow default nodes can be repositioned by mouse drag.
- Node cards no longer expose an inline delete button.
- Non-fixed nodes are deleted from keyboard focus with `Enter`, `Delete`, or `Backspace`; START and END stay protected.
- Workflow left panel no longer duplicates node creation. Node creation is handled from the centered bottom toolbar.

## Gates

- Frontend unit: `npm run test:unit` passed, 18 files / 34 tests.
- Frontend build: `npm run build` passed.
- Browser e2e/UAT on `http://127.0.0.1:15182` passed:
  - `workflow-tabs`
  - `workflow-node-interactions`
  - `workflow-canvas`
  - `workflow-config`
  - `workflow-variable`
  - `workflow-test-run`
  - `workflow-publish`
  - `chatflow-entry`
  - `chatflow-shared-graph`
  - `chatflow-variables`
  - `chatflow-conversation-run`
  - `chatflow-publish`

## Local Screenshots

PNG screenshots are generated locally under this folder and intentionally ignored by Git via
`artifacts/**/*.png`.
