# 101 Edge Insert Stale State Current Gate

- Date: 2026-06-09
- Scope: edge midpoint `+` button visibility and stale selected/hovered state.

## Evidence

- `current-chatflow-visibility.txt`: chatflow edge insert button hides after leaving hover, stays only while selected, and clears after pane click or palette close.
- `current-workflow-hover-only.txt`: create-page edge hover shows the insert button, leaving hover hides it, selected edge uses selected styling instead of stale hover styling.

## Result

Current regression gates pass. No product code change was required in this slice.
