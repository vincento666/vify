# Browser UAT

Date: 2026-06-07

Target: http://127.0.0.1:5173/chatflows/create

Verified:

- Clicking the left dialog settings collapse button no longer collapses the canvas into the zero-width grid column.
- Collapsed dialog settings leaves Start and End nodes visible on the canvas.
- The bottom toolbar stays visible and centered in the available canvas area.
- The chatflow test-run `运行参数` header now uses the same lightweight section title style as node config panels: transparent background, no card border, chevron + title + summary.

Root Cause:

- When the resource aside was removed by `v-if`, the canvas stage became the first grid child and was auto-placed into the collapsed `0` column.
- The fix pins the stage/open surface to the second grid column and resets to column 1 only in compact single-column media layout.

Screenshot:

![collapse and run header UAT](screenshots/browser-uat-collapse-header.png)

## Current Regression UAT

Date: 2026-06-08

Target: http://127.0.0.1:5173/chatflows/create

Verified in the in-app browser:

- Clicking `折叠侧栏` detaches the dialog settings panel instead of collapsing the canvas into a zero-width column.
- The canvas stage remains visible with width `877`.
- Start and End nodes remain visible with widths around `231`.
- The bottom toolbar remains visible with left coordinate `218.75`.

Screenshot:

![current collapse UAT](screenshots/browser-uat-current-collapse.png)
