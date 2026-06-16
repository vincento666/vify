# Plan 111

## 111.1 MVP Persistence Compatibility Evidence

- Capture RED evidence that the current MySQL8 MVP persistence proof omits at
  least one active demo persistence surface.
- Extend the existing MySQL8 runtime/customer-assistant persistence test instead
  of duplicating large fixtures.
- Add a deterministic local MySQL8 dialect/schema proof that runs without a
  MySQL service and compiles the covered table DDL under the MySQL dialect.
- Keep the existing opt-in real MySQL8 test path honest: run it only when
  `HIFY_MYSQL8_TEST_DATABASE_URL` is available, otherwise record an explicit
  skip.

## Gates

- RED:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/red.txt`
- Focused local/optional MySQL8:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/integration.txt`
- Ruff:
  `artifacts/slices/111-mysql8-runtime-v2-demo-persistence/111.1/ruff.txt`
- Browser UAT is not applicable because this slice changes persistence evidence
  only.
