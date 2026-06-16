# Plan 090

## 090.1 Explicit Check Mode

- Add RED lifespan coverage proving `check` mode must call a schema validator
  while still avoiding startup DDL.
- Add RED database coverage for missing table/column diagnostics.
- Implement a dialect-aware schema validator in `app.core.database`.
- Wire `app.main` check mode to the validator.

## Gates

- RED unit failures before implementation.
- Green focused unit tests for lifespan and schema validation.
- Ruff for touched backend/test files.
- Browser UAT is not applicable because this is backend startup behavior only.
