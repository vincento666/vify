## Current Node Panel UAT

Date: 2026-06-08

Validated current workflow node panel baseline after the chatflow left-panel fixes.

### Condition / Selector

- E2E: `e2e-condition-branch-values-current.txt`
- Screenshot: `condition-branch-values-current.png`
- Result: PASS
- Coverage:
  - selector card renders branch blocks rather than generic input/output rows
  - branch names are shown in the card and panel and can be edited from the panel header area
  - branch output handles align to the matching branch rows
  - panel supports if / else-if / else, priority labels, typed operators, variable reference chips, and default branch

### Variable Aggregation

- E2E: `e2e-variable-aggregation-official-current.txt`
- Screenshot: `variable-aggregation-official-current.png`
- Result: PASS
- Coverage:
  - group name renders as a group header, not as a variable row
  - group variables use compact Coze-like reference/value rows
  - selecting or filling a row keeps an empty trailing input row for the next variable
  - no advanced/compat settings are visible in the panel

### Variable Assignment

- E2E: `e2e-variable-aggregation-assignment-current.txt`
- Screenshot: `variable-aggregation-assignment-current.png`
- Result: PASS
- Coverage:
  - assignment target and source use the shared variable reference/value control
  - operation assignment exposes the numeric operator control
  - workflow and chatflow routes share the same panel behavior
