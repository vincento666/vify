# UAT

Date: 2026-06-09

Target:
- http://127.0.0.1:5173/workflows/create

Validation:
- Dragging a connection from START to END within the magnetic radius highlights the target endpoint with the connection-preview state.
- The endpoint dot scales up while the pointer is still within the magnetic radius, before the mouse is released.
- Releasing the pointer creates the edge.

Local screenshot:
- `artifacts/slices/120-endpoint-magnetic-preview/uat-endpoint-magnetic-preview.png`

Notes:
- Current implementation already satisfies the requested endpoint magnetic preview behavior; this slice adds regression coverage and evidence rather than changing production code.
