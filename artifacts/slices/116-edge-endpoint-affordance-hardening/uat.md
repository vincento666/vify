# 116 Edge Endpoint And Right Panel UAT

Date: 2026-06-09

Target: `http://127.0.0.1:5173/workflows/6217/canvas`

Checks:

- Reloaded the in-app browser and measured a static canvas endpoint.
- Endpoint 1x dot width is `10.5px`, matching `0.75rem` at the current `14px` root size.
- Opened a workflow node config panel and debug dock together.
- Config panel top gap relative to the canvas, right screen gap, and bottom screen gap are all `8.75px`.
- Debug dock left and bottom screen gaps are also `8.75px`; dock to config gap is `15.75px`.
- Opened the workflow test run panel with the debug dock.
- Test run panel top gap relative to the canvas, right screen gap, and bottom screen gap are all `8.75px`.
- Variable assignment panel contains no `.variable-assignment-task` intro block and no `fx` operation toggle.

Screenshot:

- `screenshots/in-app-uat-workflow-6217.png`
