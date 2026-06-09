# UAT

Date: 2026-06-09

Target:
- http://127.0.0.1:5173/workflows/{generated}/canvas

Validation:
- Hovering a node highlights every edge connected to that node while preserving hover-width styling.
- Selecting a node applies the selected-edge visual treatment to every connected edge.
- Existing line hover, line selection, and edge-insert plus button behavior still pass their regression scripts.

Artifact:
- `artifacts/slices/119-node-edge-highlight/uat-node-edge-highlight.png`
