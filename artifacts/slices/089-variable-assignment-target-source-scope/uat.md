# Browser UAT - 089 Variable Assignment Target Scope

Date: 2026-06-08
Target: workflow variable assignment panel, current local app on http://127.0.0.1:5173/workflows/6217/canvas

## Result
- PASS: The variable assignment target field is readonly and opens a picker instead of accepting arbitrary new variable names.
- PASS: The target picker no longer treats the current assignment node target as a configured writable variable.
- PASS: The value side still uses the shared literal/reference split control and keeps the existing selected upstream variable chip.
- PASS: No explicit source type selector is rendered in the assignment row.

## Evidence
- RED: red.txt fails on the old target-picker scope leak.
- E2E: e2e-assignment.txt passes after implementation.
- Unit/rem: rem-unit.txt and full-unit.txt are green.
- Integration: integration.txt is green for variable aggregation/assignment roundtrip.
- Build: build.txt is green.
