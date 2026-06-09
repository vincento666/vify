# UAT

Date: 2026-06-09

Targets:
- http://127.0.0.1:5173/workflows/{generated}/canvas

Validation:
- Condition node card is a branch-specialized card, not a generic input/output node.
- Branch labels remain semantic and editable.
- Branch blocks and right-side source endpoints stay visually aligned after branch rename.
- Config panel supports variable references, comparison operators, branch add/rename, and default branch display.
- Runtime selects the correct downstream branch for matching/default conditions.

Local screenshots:
- `artifacts/slices/122-condition-node-parity/uat-condition-branch-endpoints.png`
- `artifacts/slices/122-condition-node-parity/uat-condition-branch-values.png`
