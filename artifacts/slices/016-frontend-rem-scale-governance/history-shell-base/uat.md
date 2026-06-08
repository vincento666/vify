## Frontend shell/base rem closure

Date: 2026-06-09

### Scope

- Install the global UI scale controller in `frontend/src/main.ts`.
- Convert shell chrome sizing in `frontend/src/App.vue` from raw px props/styles to rem and design tokens.
- Convert global shell/button/card spacing in `frontend/src/styles/global.css` and token values in `frontend/src/styles/tokens.css` to rem-based defaults.
- Bridge Element Plus table column width props through `normalizeElementTableSize()` so existing numeric-pixel table internals can still receive numbers while app code can author rem.
- Keep Observe/debug surfaces out of top-level composer navigation.

### Gates

- `targeted-unit-rem.txt`: passed.
- `full-unit.txt`: passed.
- `build.txt`: passed.

### Notes

- This is a historical cleanup commit for work already present in the worktree.
- Browser-level visual UAT for workflow/chatflow canvas was already covered in the later workflow/chatflow gates; this slice only records the shared shell/base rem closure.
