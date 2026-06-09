# 133 Current Affordance Audit

## Scope

Evidence-only audit for recent canvas interaction concerns that now pass without further production changes.

## Verified

- Node hover highlights connected edges without selecting them.
- Node selection applies selected edge styling to connected edges and clears on pane click.
- Edge midpoint insert button hides when neither hovered nor selected.
- Edge insert palette interactions still split edges correctly.
- Endpoint visible dot and 3x hit area stay separate, so edges anchor to the visible dot while magnetic hover remains easy to hit.
- Workflow and Chatflow node palettes differ by mode as intended.
- Chatflow left settings panel header controls do not overlap.
- Collapsing workflow/chatflow left panel does not blank the canvas.

## Evidence

- `node-edge-highlight.txt`
- `edge-insert-button-visibility.txt`
- `edge-insert-hover-only.txt`
- `endpoint-affordances.txt`
- `endpoint-magnetic-preview.txt`
- `node-palette-modes.txt`
- `chatflow-left-panel-settings.txt`
- `chatflow-settings-collapse-canvas.txt`
- `left-panel-collapse-visibility.txt`

## Result

PASS. No production patch was needed for these checks.
