# 129 MySQL8 One-Click Demo Seed Gate

## Status

Slice 129.1 complete. Local one-click seed reports now include a sanitized
persistence fingerprint. The opt-in real MySQL8 seed command gate is present
and skipped explicitly when `HIFY_MYSQL8_TEST_DATABASE_URL` is not set.

## Goal

Close the productized MVP demo persistence proof by making the one-click demo
seed report declare the database persistence fingerprint used for the run and
by preserving an opt-in MySQL8 seed command gate.

## Acceptance Criteria

- The one-click seed JSON report includes a non-secret `persistence` section
  with database dialect, sanitized URL kind, MySQL live round-trip flag, and
  topology counts.
- Local deterministic tests prove the report shape without needing live provider
  credentials, while product demo seed gates use MySQL8 only.
- An opt-in MySQL8 test runs the real one-click seed command when
  `HIFY_MYSQL8_TEST_DATABASE_URL` is available and records the same topology
  counts with `dialect=mysql`.
- Report output must not include API keys, passwords, or raw secret-looking
  values.

## Non-goals

- Do not provision MySQL automatically.
- Do not alter demo story data or customer-assistant runtime semantics.
- Do not add frontend UI changes.

## Evidence

Evidence lives under
`artifacts/slices/129-mysql8-one-click-demo-seed-gate/129.1/`.
