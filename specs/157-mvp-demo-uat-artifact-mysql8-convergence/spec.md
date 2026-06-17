# Spec 157: MVP Demo UAT Artifact MySQL8 Convergence

## Status

Slice 157.1 complete.

## Goal

Prevent the productized MVP demo browser UAT evidence from drifting back to
SQLite. Slice 115 was later superseded by the MySQL8-only boundary, but its
local runtime artifacts can still retain old seed and dev-server commands. Those
artifacts must be clean enough that a future operator cannot copy a SQLite UAT
command by accident.

## Functional Requirements

- Scan the current slice 115 browser UAT artifact directory when it exists.
- Reject textual 115 UAT artifacts that retain SQLite URLs, SQLite wording, or
  the old `hify-uat.db` file reference.
- Reject SQLite database files under the current 115 UAT artifact directory.
- Reject tracked product demo and live acceptance specs that still prescribe
  SQLite runtime databases.
- Keep the existing MySQL8 boundary checks for docs, specs, application code,
  scripts, and runtime-adjacent tests.

## Non-Goals

- Do not rerun the full 115 browser UAT.
- Do not scan historical RED evidence from other specs where SQLite appears as
  expected failure output.
- Do not reintroduce a local SQLite fallback for unit, integration, contract, or
  e2e tests.

## Acceptance Criteria

- RED evidence shows the new artifact scan fails against the stale 115.1 SQLite
  evidence.
- The stale local 115.1 artifact text is rewritten to MySQL8-only command
  evidence, and stale SQLite database files are absent.
- Product demo and live acceptance specs no longer contain SQLite runtime
  instructions.
- Focused MySQL8 boundary unit tests pass.
- A final local scan of the 115.1 artifact directory reports no SQLite markers.

## Evidence

Evidence lives under
`artifacts/slices/157-mvp-demo-uat-artifact-mysql8-convergence/157.1/`.

- RED 115 artifact scan: `red.txt`
- RED product spec scan: `spec-red.txt`
- Unit: `unit.txt`
- Final scans: `artifact-scan.txt`, `spec-scan.txt`, `runtime-scan.txt`
