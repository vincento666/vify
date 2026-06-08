## 043 Endpoint Connection Radius UAT

- URL: `http://127.0.0.1:5173/chatflows/{generated}/canvas`
- Scenario: drag from `START` source endpoint toward the `LLM` target endpoint and stop 30px before the target center.
- Expected: target endpoint is treated as connectable inside the enlarged connection radius and scales to 1.5x while the pending edge is still being dragged.
- Result: PASS.
- Screenshot: `screenshots/e2e-endpoint-radius.png`

Notes:
- `CANVAS_CONNECTION_RADIUS = 44` is an interaction radius in VueFlow canvas screen coordinates, so it intentionally remains a numeric canvas/device-pixel value rather than a visual CSS `rem` token.
- Follow-up regression also passed for node hover 1.2x, endpoint hover 1.5x, and selected-node endpoint 1.2x.
