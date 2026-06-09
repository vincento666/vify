# 132 Add Node Palette Density UAT

## Scope

- Unified bottom toolbar and edge midpoint add-node palettes to the same compact footprint.
- Palette target density:
  - width <= 16.5rem;
  - row height <= 2.1rem;
  - font <= 0.8125rem;
  - search input <= 2.1rem;
  - bottom/edge width delta <= 0.25rem.

## Evidence

- RED: `red.txt`
- E2E: `e2e.txt`
- Screenshot UAT: `palette-uat.png`
- Panel regression: `panel-polish.txt`
- Frontend rem: `rem.txt`
- Full frontend unit: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`

## Result

PASS. The palette is compact and consistent across bottom toolbar and edge insert entrypoints.
