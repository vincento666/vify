# 073 Plan

## Slice 073.1: Idempotent MVP Demo Seed

Build a backend seed module and command that composes the existing RuntimeLab
airline Chatflow seed with customer-assistant and knowledge demo records.

Implementation shape:

- Add a reusable seed module under `app/modules/customer_assistant/infra/` or a
  neutral demo bootstrap module if cross-module imports become cleaner.
- Add `scripts/seed_mvp_demo.py` as the public command.
- Reuse `seed_runtime_lab_airline_chatflows()` for Chatflow SOP topology.
- Keep all generated environment output non-secret, following
  `write_runtime_lab_env()`.
- Store demo story metadata in JSON-friendly records that later UAT scripts can
  resolve deterministically.

TDD seams:

- RED unit/integration test proves no single MVP seed API exists yet.
- Unit tests cover story catalog shape, secret-free env writer behavior, and
  idempotent builders.
- Integration tests run against isolated SQLite first and use existing MySQL8
  opt-in conventions when `HIFY_MYSQL8_TEST_DATABASE_URL` is available.
- E2E/browser gates can start with deterministic smoke checks and become richer
  in 078.

## Slice ownership

- 073 owns `scripts/`, seed modules, seed tests, `docs/mysql8-weaviate-demo.md`,
  and spec artifacts.
- 073 should not edit customer-assistant runtime hot paths unless a test proves a
  hard seed-only blocker.
- 074 owns the customer-service workbench loop after this seed exists.

## Gates

1. RED: run the new seed test before implementation and save the expected
   failure.
2. Unit: seed helpers and secret-free writer pass.
3. Integration: isolated DB seed is idempotent and creates required topology.
4. E2E: seeded data supports one customer-assistant API smoke and one
   RuntimeLab binding smoke.
5. Browser UAT: seeded app surfaces load without horizontal overflow or missing
   demo labels.
6. Docs: update demo bootstrap instructions and this task list.
