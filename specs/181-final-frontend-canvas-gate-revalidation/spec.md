# Spec 181: Final Frontend Canvas Gate Revalidation

## Status

Complete.

## Goal

Refresh frontend gate evidence for the 071 responsive canvas closure on the
current branch. This slice does not change product behavior; it proves the
workflow/chatflow canvas responsive policy, rem governance, full frontend unit
suite, production build, and browser phase UAT are green after the latest MVP
backend and MySQL8 hardening work.

## Functional Requirements

- Reuse the checked-in 071 RED evidence as the historical regression anchor.
- Run focused responsive canvas and rem governance tests.
- Run the full frontend unit gate.
- Run the frontend production build.
- Run the real browser canvas phase UAT for workflow and chatflow creation
  routes, saving measurements and screenshots.
- Save outputs under
  `artifacts/slices/181-final-frontend-canvas-gate-revalidation/181.1/`.

## Non-Goals

- Do not change production frontend behavior unless a revalidation gate exposes
  a real regression.
- Do not run customer-assistant demo UAT in this slice.
- Do not run live LLM provider gates in this slice.

## Acceptance Criteria

- [x] Focused responsive/rem tests pass.
- [x] Full frontend unit gate passes.
- [x] Frontend build passes.
- [x] Browser phase UAT passes and records workflow/chatflow screenshots for
  wide, right-anchored, right-shelved, stage-shelved, and left-rail widths.
- [x] Artifact scan does not include OpenRouter API key material.

## Evidence

Evidence is saved under
`artifacts/slices/181-final-frontend-canvas-gate-revalidation/181.1/`.

- RED anchors:
  `red-responsive-anchor.txt` and `red-right-anchored-anchor.txt`.
- Focused responsive/rem:
  `frontend-focused-rem.txt` passed 4 files and 11 tests.
- Full frontend unit:
  `frontend-unit.txt` passed 91 files and 367 tests.
- Frontend build:
  `frontend-build.txt` passed `vue-tsc` and Vite production build.
- Browser UAT:
  `browser-uat.txt` passed the checked-in phase verifier.
- Measurements:
  `browser-measurements.json` records 10 phase checks, 5 workflow and 5
  chatflow, with zero phase mismatches and zero document horizontal overflow.
- Screenshots:
  `screenshots/` contains workflow and chatflow captures for wide,
  right-anchored, right-shelved, stage-shelved, and left-rail phases.
- Artifact scan:
  `artifact-scan.txt` is empty for OpenRouter key material and historical
  SQLite database markers.
