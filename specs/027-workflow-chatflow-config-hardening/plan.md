# Plan 027: Workflow/Chatflow Config Hardening

## Implementation Notes

- Keep backend payload compatibility; add metadata only where old payloads can
  be inferred safely.
- Prefer behavior tests through UI/E2E and public frontend helpers.
- Preserve existing Workflow/Chatflow route/API envelopes.
- Use rem-only visual units and run rem governance on every frontend slice.

## Public Interfaces

- Start variables gain a local `builtIn`/locked marker in normalized frontend
  config.
- Trial-run payload builders filter default runtime/message variables from
  extra user input.
- Condition branch config remains serializable as `conditionBranches` but can
  carry structured left/right value metadata for UI and runtime evaluation.
