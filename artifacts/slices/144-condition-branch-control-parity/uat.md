# 144 Condition Branch Control Parity UAT

- Date: 2026-06-09
- Target: `http://127.0.0.1:5173/workflows/{created}/canvas`
- Scope: workflow condition node branch editor.

## Checks

- Left condition operand is a dropdown-style variable selector with a chevron.
- Left condition operand has no editable input surface.
- Right condition operand keeps a literal input plus a persistent variable picker button.
- Right condition operand displays a read-only type prefix derived from the selected left variable.
- Static unused groups such as user/application/session/system variables are not shown in the condition picker for this local workflow context.
- Variable selection inserts `{{start.intent}}` and renders chips with clear actions.
- Empty-check operators clear and disable the right operand.

## Evidence

- E2E: `artifacts/slices/144-condition-branch-control-parity/e2e.txt`
- Unit: `artifacts/slices/144-condition-branch-control-parity/unit.txt`
- rem gate: `artifacts/slices/144-condition-branch-control-parity/rem.txt`
- Screenshot: `artifacts/slices/144-condition-branch-control-parity/screenshots/condition-branch-values.png`

Note: in-app browser automation did not expose an active tab handle in this turn, so visual UAT was captured with Playwright Chromium against the same local app URL.
