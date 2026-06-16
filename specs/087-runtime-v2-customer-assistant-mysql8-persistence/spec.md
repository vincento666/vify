# Spec 087: Runtime V2 + Customer Assistant MySQL8 Persistence

## Goal

Add a focused real-MySQL8 persistence gate for the productized MVP demo state
owned by runtime v2, RuntimeLab SOP routing, and the customer assistant ledger.

## Acceptance Criteria

- A MySQL8 integration test creates the runtime v2, RuntimeLab, and customer
  assistant persistence tables against `HIFY_MYSQL8_TEST_DATABASE_URL`.
- The test persists and reads back nested JSON for Chatflow session/event/
  checkpoint/channel state, published Workflow snapshots, RuntimeLab checkpoint
  and command state, and customer assistant session/run/task/event/worker/action
  state.
- The test proves representative MySQL unique constraints reject duplicate
  runtime and customer-assistant events or idempotency keys.
- The test is skipped without an explicit MySQL8 URL, and the skip is treated as
  environment-blocked evidence rather than final product completion.

## Non-goals

- Do not introduce Alembic migrations in this slice.
- Do not require Docker or provision MySQL implicitly from the test.
- Do not cover vector tables; MySQL demo mode keeps vectors in Weaviate.

## Evidence

Evidence lives under
`artifacts/slices/087-runtime-v2-customer-assistant-mysql8-persistence/087.1/`.
