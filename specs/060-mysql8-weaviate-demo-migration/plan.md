# Plan 060: MySQL8 + Weaviate Demo Migration

## Strategy

Make MySQL8 primary DB for demo business data. Keep semantic vectors in
Weaviate.

```text
Business persistence -> MySQL8
Semantic vector search -> Weaviate
Keyword/FAQ exact/RRF -> app/domain layer
```

No production data migration. No dual-write. No MySQL-native vector search.

## Phase 1: Dialect Inventory

Collect hard facts:

```text
.returning() usage
pgvector Vector usage
postgresql-only vector SQL
Alembic compatibility
JSON defaults
Boolean/default expressions
index/unique length
raw SQL and dialect.name branches
```

Artifacts:

```text
060.1-dialect-inventory/
  returning-inventory.txt
  vector-coupling-inventory.txt
  mysql-ddl-compile.txt
  risk-register.md
```

## Phase 2: Write Compatibility

Design small helper:

```text
insert_and_fetch(session, table, values, key_column="id")
update_and_fetch(session, table, where, values, key_column="id")
```

Rules:

```text
PostgreSQL may use RETURNING internally.
MySQL8 uses lastrowid / rowcount + select.
Services do not know dialect.
```

Migrate repositories gradually:

```text
provider
mcp
agent
chat
knowledge
workflow
evaluation
runtime_policy
runtime_lab
customer_assistant
handoff
audit
```

## Phase 3: MySQL8 Alembic

Target:

```text
docker/local MySQL8
HIFY_DATABASE_URL=mysql+pymysql://...
alembic upgrade head
```

Required fixes:

```text
skip or replace pgvector tables/indexes in MySQL path
remove JSON server defaults if unsafe
verify BIGINT AUTO_INCREMENT
verify bool defaults
verify utf8mb4 index lengths
generate schema-mysql8.sql
```

## Phase 4: Weaviate Vector Store

Config:

```text
HIFY_VECTOR_STORE=weaviate
HIFY_WEAVIATE_URL=http://127.0.0.1:8080
HIFY_WEAVIATE_API_KEY=optional
```

Flow:

```text
document import
  -> MySQL document/document_chunk metadata
  -> embedding provider
  -> Weaviate upsert

FAQ create/import/update
  -> MySQL FAQ row
  -> embedding provider
  -> Weaviate upsert

semantic retrieval
  -> Weaviate search
  -> hydrate metadata from MySQL if needed
```

Consistency:

```text
delete document -> delete/deactivate vectors
delete FAQ -> delete/deactivate vectors
reimport -> idempotent replace
Weaviate down -> explicit error or configured degraded mode
```

## Phase 5: Module Smoke

Run MySQL8-backed smoke:

```text
health/readiness
provider CRUD
mcp CRUD
agent CRUD/version/publish
chat session/message
knowledge metadata + Weaviate retrieval
workflow create/save/run metadata
chatflow create/save/run metadata
evaluation set/evaluator/experiment/report
runtime policy profile/release/decision log
customer assistant session/run/task/event/action
audit/handoff
frontend browser smoke
```

## Phase 6: Docs

Add:

```text
.env.example.mysql8-weaviate
docker-compose.mysql8-weaviate.yml or equivalent doc
MySQL init: alembic upgrade head
Weaviate init: schema/class auto-create or script
known limits: demo only, no dual-write, no MySQL vector search
```

## Test Matrix

```text
Unit:
  write helper
  vector-store selection
  MySQL schema branching

Integration:
  real MySQL8 Alembic
  real MySQL8 repository CRUD
  real or controlled Weaviate upsert/search/delete

Contract:
  API envelope unchanged
  frontend API calls unchanged

UAT:
  knowledge semantic retrieval via Weaviate
  frontend smoke against MySQL8 backend
```

## Rollback

Demo rollback:

```text
unset MySQL HIFY_DATABASE_URL
unset HIFY_VECTOR_STORE=weaviate
return to sqlite:///./hify.db
```

Implementation must keep rollback simple by isolating dialect logic in helpers
and config, not services.

## Open Questions

- Should MySQL8 path create embedding metadata mirror tables, or skip them
  entirely?
- Should Weaviate schema be auto-created at app startup or via script?
- Should demo default use fake embeddings for deterministic startup?
- Should Weaviate failure hard-fail semantic retrieval or fallback to keyword?
