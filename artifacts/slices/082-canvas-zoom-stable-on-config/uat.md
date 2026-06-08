# Browser UAT

- URL: generated workflow canvas from `workflow-config-panel-zoom-stability.mjs`.
- Viewport: 1440x900.
- Scenario: open workflow canvas, click the LLM node to open the config panel, then close the panel.
- Expected: the canvas and node card keep their original visual scale; the right config panel does not squeeze the VueFlow surface.
- Result: passed.

Screenshot:
- `artifacts/slices/082-canvas-zoom-stable-on-config/screenshots/workflow-config-panel-zoom-stability.png`
