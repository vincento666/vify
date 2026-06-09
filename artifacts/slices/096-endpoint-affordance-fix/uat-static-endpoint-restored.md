# UAT - Static Endpoint Size Restored

Target: http://127.0.0.1:5173/workflows/6217/canvas

Browser metrics after reload:
- `--node-port-dot-size`: `1rem`
- `--node-port-hit-size`: `3rem`
- rendered static dot: `14px` in current rem-scaled viewport
- rendered hitbox: about `35px` after current canvas viewport transform
- screenshot: `artifacts/slices/096-endpoint-affordance-fix/uat-static-endpoint-restored.png`

Verdict: static node endpoints no longer use the shrunken `0.875rem` baseline; hover/connection affordances scale from the restored `1rem` baseline.
