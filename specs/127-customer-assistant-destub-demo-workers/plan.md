# Plan: Customer Assistant Destub Demo Workers

## Slice 127.1 Backend Seed/Profile Destub

1. Add focused RED tests for MVP seed topology, default profile catalog JSON,
   and deterministic worker behavior.
2. Replace seeded `flight_status` demo task routing with a productized
   configured worker type/ref while preserving deterministic output.
3. Rename default baggage QA profile away from stub terminology and route it to
   the same productized deterministic worker type.
4. Keep legacy `stub_qa` runtime/router compatibility untouched unless a gate
   proves it is part of the seeded/default MVP surface.
5. Run focused unit and integration gates, ruff touched files, update evidence,
   then commit only this slice.

## Test Strategy

- Unit: default worker profile catalog JSON and deterministic worker output.
- Integration: seeded MVP demo customer-assistant tasks persisted to the
  database, including `worker_type`, `worker_ref`, and generated env profile
  JSON.
- Additional focused integration: worker-profile API override compatibility and
  one-click MVP bootstrap verification.
- Browser UAT: not required for 127.1 because no frontend files or browser
  interactions change.

## Result

Slice 127.1 is complete. Seeded/default MVP customer-assistant worker routes no
longer expose productized-demo `stub_qa` markers; legacy `stub_qa`
compatibility remains available only through explicit test/config overrides.
