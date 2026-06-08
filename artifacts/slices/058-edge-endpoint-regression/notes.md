## Slice Notes

- Scope: regression evidence for edge insert button visibility, edge insertion, branch edge split/reconnect, and endpoint hover/connection affordances.
- No product code changed in this slice.
- Added the branch-edge insertion E2E asset to version control so condition/intent branch edges preserve their `condition` when split by the inline `+` insertion affordance.
- Gates passed:
  - `chatflow-edge-insert-button-visibility`
  - `chatflow-edge-interactions`
  - `chatflow-edge-insert-branch`
  - `chatflow-endpoint-connection-radius`
  - `chatflow-endpoint-affordances`
