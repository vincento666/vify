# Spec 178: Live LLM Artifact MySQL8 Convergence

## Status

Slice 178.1 complete.

## Goal

Prevent live LLM acceptance evidence from retaining stale SQLite instructions.
The productized MVP demo now treats MySQL8 as the only runtime database for live
and browser UAT gates, so local live artifacts must not teach future operators to
copy old SQLite commands or notes.

## Functional Requirements

- Scan current local live LLM artifact directories when they exist.
- Reject SQLite database wording, SQLite URLs, and stale local DB filenames in
  live acceptance artifacts.
- Preserve historical RED evidence in unrelated slices; this guard only covers
  current live LLM artifact directories.

## Non-Goals

- Do not rerun live OpenRouter gates.
- Do not scan every historical artifact where SQLite appears as expected RED
  output.

## Acceptance Criteria

- RED unit test fails against stale 135/136 live artifact SQLite wording.
- Stale local artifact notes are rewritten to MySQL8-only wording.
- Focused MySQL8 boundary unit tests pass.

## Evidence

Evidence lives under
`artifacts/slices/178-live-llm-artifact-mysql8-convergence/178.1/`.

- RED: `red.txt`
- Unit: `unit.txt`
- Final scans: `artifact-scan.txt`, `secret-scan.txt`
