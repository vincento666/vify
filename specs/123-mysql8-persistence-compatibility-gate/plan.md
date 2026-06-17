# Plan 123: MySQL8 Persistence Compatibility Gate

## Slice 123.1

Turn the existing MySQL8 concern into a concrete MVP compatibility gate.

## Approach

1. Register the baseline, runtime lab, and customer-assistant table metadata.
2. Define a compact MVP coverage manifest inside the test so missing persisted
   surfaces fail loudly.
3. Compile the target table set with `sqlalchemy.dialects.mysql.dialect()` and
   assert MySQL-compatible column types for JSON/datetime/text payload columns.
4. Use an in-memory SQLite engine for deterministic local insert/read behavior,
   exercising the same SQLAlchemy table contracts and representative payloads.
5. Preserve the opt-in live MySQL8 test via `HIFY_MYSQL8_TEST_DATABASE_URL`;
   skipping without credentials is expected and visible.

## Test Target

```bash
rtk env PYTHONPATH=. uv run pytest -rs tests/integration/mysql8/test_mysql8_runtime_v2_customer_assistant_persistence.py
```

## Evidence

- `artifacts/slices/123-mysql8-persistence-compatibility-gate/123.1/red.txt`
- `artifacts/slices/123-mysql8-persistence-compatibility-gate/123.1/focused.txt`
- `artifacts/slices/123-mysql8-persistence-compatibility-gate/123.1/ruff.txt`
- `artifacts/slices/123-mysql8-persistence-compatibility-gate/123.1/live-mysql.txt`

Live MySQL8 uses the existing `HIFY_MYSQL8_TEST_DATABASE_URL` convention. When
the variable is absent, pytest reports an explicit skip with the setup message.

## Risk Notes

- The local gate cannot prove server-specific MySQL JSON behavior, but it catches
  dialect compile failures and repository/table contract drift without requiring
  external services.
- Live MySQL8 coverage remains available for environments with credentials.
