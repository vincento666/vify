# Browser UAT - 091 Variable Assignment Operation UI

Date: 2026-06-08
Target: workflow variable assignment node panel

## Result
- PASS: Assignment source exposes a first-class `fx` operation-assignment entry.
- PASS: Clicking `fx` renders compact operator and operand controls in one row.
- PASS: The operation UI can switch back to normal literal/reference input mode.
- PASS: Clicking the SVG/icon target picker trigger can close the target picker; SVG targets are treated as internal picker controls.

## Evidence
- RED: red-ui.txt failed when operation assignment entry was missing.
- E2E: e2e-assignment.txt passed and screenshot is saved at `screenshots/assignment-operation-ui.png`.
- Unit/rem: rem-unit.txt and full-unit.txt passed.
- Build: build.txt passed.
