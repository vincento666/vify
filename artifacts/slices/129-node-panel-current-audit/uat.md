## UAT

- Reproduced the compact chatflow canvas geometry failure in `chatflow-settings-collapse-canvas.mjs`.
- Verified the fix in a real Playwright browser at `877x832`: the right test-run panel remains anchored to the screen right, the toolbar stays in the available canvas, and start/end nodes are refit left of the panel.
- Confirmed chatflow left settings, trial panel, publish/open shell, workflow/chatflow layout, toolbar zoom, config panel, edge insert hover-only, all-node variable references, resource panels, transform nodes, six-node matrix, endpoint magnetic preview, node-edge highlight, and workflow/chatflow canvas lifecycle regressions.
- Screenshot: `chatflow-settings-collapse-canvas.png`.

## Gates

- RED: `red-chatflow-settings-collapse-canvas.txt`
- E2E: current `e2e-*.txt` files in this directory.
- rem: `rem.txt`
- Unit: `unit.txt`
- Build: `build.txt`
