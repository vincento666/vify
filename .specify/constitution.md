# Hify Python Migration Constitution

## Mission

Rebuild Hify on Python 3.12, FastAPI, SQLAlchemy 2.0, and Alembic while preserving
the existing product boundary, frontend-visible behavior, API contract, and
deployment ergonomics. The migration follows the original project's staged
delivery order and uses Spec Kit records as the source of truth.

## Core Principles

### 1. Replica Before Expansion

Features `001` through `008` replicate the current Java/Spring Boot product
boundary, including current mock behavior. They must not silently introduce new
business scope. Real pgvector RAG and real tool/MCP behavior are handled only in
`009` and `010`.

### 2. Contract Compatibility

The existing frontend contract is preserved:

- routes stay under `/api/v1/...`;
- response envelope stays `{code, message, data}`;
- pagination shape stays compatible with current `PageResult`;
- SSE event payloads keep `type=delta|done|error` semantics.

Any deliberate contract break requires an ADR and frontend migration slice.

### 3. Test-First Slice Gates

Every slice is executed with RED -> GREEN -> REFACTOR. The RED failure must be
captured before production code is added. A slice is not complete until unit,
integration/contract, E2E, browser UAT, and documentation gates pass.

### 4. Small Vertical Slices

Slices must cut through the public behavior: API, service, persistence, and
user-visible outcome when applicable. Horizontal work such as "create all ORM
models" is allowed only inside a slice that proves a behavior.

### 5. Runtime Boundary Discipline

FastAPI routes must stay thin. Long-lived streaming must not hold SQLAlchemy
sessions. External HTTP and LLM calls use async clients and explicit concurrency
limits. Background tasks must be tracked and bounded.

### 6. Database Truth Through Alembic

The Python schema is owned by Alembic. The baseline must reconcile the current
MySQL DDL and the richer H2 mock DDL before feature implementation proceeds.

### 7. Observable, Reproducible Delivery

Each slice records commands, outputs, screenshots, and UAT notes under
`artifacts/slices/`. A future agent must be able to understand what passed and
why from those artifacts and spec files alone.

## Quality Gates

For each slice:

1. `RED` gate: failing test proves missing behavior.
2. `Unit` gate: focused tests pass.
3. `Integration/Contract` gate: public API and persistence behavior pass.
4. `E2E` gate: automated user path passes when UI is involved.
5. `Browser UAT` gate: real browser result is verified and captured.
6. `Docs` gate: spec/task status and evidence links are updated.

## Governance

- A slice may be split when its RED test cannot be stated as one observable
  behavior.
- A slice may not be skipped because implementation seems obvious.
- Mock-to-real replacement must not happen before the replica spec for that
  feature is green.
- Database changes require both Alembic migration and contract/integration tests.
