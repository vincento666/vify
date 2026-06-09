# 025.7 Browser UAT

Date: 2026-06-05

Target: `http://127.0.0.1:5173/chatflows/1741/canvas`

## Result

PASS.

Verified in the in-app browser:

- Selecting the `start->end` edge exposes the midpoint `+` insert button.
- Clicking the midpoint `+` opens the edge insert palette with the palette edge anchored against the button center.
- Choosing `大模型` creates `llm_1`, closes the palette, selects the inserted node, and opens the LLM config panel.
- The visible graph now contains exactly `start->llm_1` and `llm_1->end`; the original `start->end` edge is gone.

## Evidence

- `uat-browser.json`
- `screenshots/uat-palette-open.png`
- `screenshots/uat-inserted-node.png`
