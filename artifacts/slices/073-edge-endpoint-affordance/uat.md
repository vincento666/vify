## 073 Edge and Endpoint Affordance UAT

- Scope:
  - Edge middle plus button must not remain visible after the insert palette is closed.
  - Edge insert palette must not trap the plus button behind its own overlay.
  - Endpoint preview scale radius must be larger than the magnetic connection radius.
- Browser/E2E evidence:
  - `chatflow-edge-insert-button-visibility.mjs` opens an edge insert palette, closes it by clicking the plus button again, moves away, and verifies no visible plus button remains.
  - `chatflow-endpoint-connection-radius.mjs` drags from a source handle to within magnetic range and verifies the target endpoint is already scaled to 1.5x.
  - `chatflow-edge-interactions.mjs`, `chatflow-edge-insert-branch.mjs`, and `chatflow-endpoint-affordances.mjs` remain green for broader edge/endpoint regression.
- Screenshot:
  - `screenshots/endpoint-preview-radius.png`
- Gates:
  - RED: `red-edge-button-toggle-stale.txt`
  - Focused unit/rem: `unit-canvas-affordance.txt`
  - Full unit: `unit-full.txt`
  - Build: `build.txt`
