# Browser UAT - 092 Edge Insert State Hardening

Date: 2026-06-08
Target: workflow/chatflow canvas edge insert button and endpoint connection radius

## Result
- PASS: Hovering a line shows the circular insert button.
- PASS: Selecting a line keeps the insert button visible with explicit selected state.
- PASS: After cursor leaves a selected line, the edge no longer carries stale hover styling.
- PASS: Pane click clears selected/hovered edge states and hides the insert button.
- PASS: Closing the edge insert palette clears stale edge state and hides the button.
- PASS: Endpoint connection preview radius matches magnetic connection radius; target endpoint receives the 3x preview scale inside the radius.

## Evidence
- RED: red-edge-state.txt failed on stale hover state after selected edge cursor leave.
- E2E: e2e-chatflow-edge-state.txt, e2e-workflow-edge-state.txt, e2e-endpoint-radius.txt passed.
- Unit/rem: rem-unit.txt and full-unit.txt passed.
- Build: build.txt passed.
- Screenshots: screenshots/chatflow-edge-state.png, screenshots/workflow-edge-hover-selected.png, screenshots/endpoint-connection-radius.png.
