## UAT

- Opened workflow canvas through Playwright browser automation with the variable aggregation node selected.
- Verified the variable aggregation panel keeps Coze-like grouped editing: group headers are read-first, click-to-edit, and output is a read-only summary.
- Verified the `Score` group infers `Number` from `{{start.score}}` and the output summary also shows `Number`.
- Verified the automatic blank candidate row remains empty after type inference; it no longer normalizes into a visible `0`.
- Screenshot: `variable-aggregation-type-inference.png`.

## Gates

- RED: `red.txt`, `red-candidate.txt`
- Unit: `nodeconfig-unit.txt`, `unit.txt`
- E2E: `e2e.txt`, `e2e-assignment.txt`
- Integration: `integration.txt`
- rem: `rem.txt`
- Build: `build.txt`
