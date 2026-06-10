# Chatflow Trial Panel Layer UAT

## Issue

The chatflow trial panel was visually below the bottom toolbar (`test-run-panel` z-index 9, toolbar z-index 45). This allowed the toolbar to layer above right-side floating panels.

## Fix

Raise `test-run-panel` and `ops-panel` to z-index 60 while keeping the selected-node test drawer above them at z-index 70.

## Evidence

- RED: `red.txt`
- E2E: `e2e-green.txt`
- Layout regression: `e2e-layout.txt`
- Zoom/drawer regression: `e2e-zoom-stability.txt`
- rem gate: `rem.txt`
- focused unit: `unit.txt`
- full unit: `full-unit.txt`
- build: `build.txt`
- In-app browser screenshot: `screenshots/in-app-chatflow-trial-layer-after-fix.png`

In-app browser post-fix metrics: trial panel z-index 60, toolbar z-index 45.
