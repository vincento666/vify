## Browser UAT

- Target: `http://127.0.0.1:5173/chatflows/create`
- Flow: hover the default `start -> end` edge, move onto the midpoint `+` insert button, then move away to blank canvas without selecting the edge.
- Result: the midpoint insert button hides once the pointer leaves both the edge and the button; selecting the edge still keeps the button visible until a pane click clears selection.
- Screenshot: `screenshots/e2e-edge-button-hidden.png`

Note: in-app Browser coordinate probing did not reliably hit the SVG edge interaction path, so the UAT evidence uses the Playwright browser E2E for the exact pointer path plus the saved screenshot. Existing `chatflow-edge-interactions.mjs` also passed to prove selected-edge and split-edge behavior remains intact.
