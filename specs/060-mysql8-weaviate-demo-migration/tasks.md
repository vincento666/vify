# Tasks 060: MySQL8 + Weaviate Demo Migration

## 060.0 Spec Setup

- [x] Use spec number `060`.
- [x] Select MySQL8 primary DB + Weaviate external vector store.
- [x] Limit scope to current demo migration.
- [x] Do not implement code in this step.

## 060.1 Dialect Inventory

- [x] RED: record failing MySQL8 Alembic smoke against current code.
- [x] Inventory every `.returning()` usage under `app/`.
- [x] Inventory pgvector-only elements: `Vector`, `ivfflat`,
  `vector_cosine_ops`, `<=>`.
- [x] Inventory raw SQL and `dialect.name` branches.
- [x] Inventory JSON columns/defaults.
- [x] Inventory Boolean/default expressions.
- [x] Inventory utf8mb4 index/unique length risks.
- [x] Generate current MySQL DDL compile artifact.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/060.1-dialect-inventory/`.

## 060.2 Repository Write Compatibility

- [x] RED: MySQL8 repository create tests fail due to `.returning()`.
- [x] Design write helper for insert/update fetch-after-write.
- [x] Migrate Provider repository.
- [x] Migrate MCP repository.
- [x] Migrate Agent repository.
- [x] Migrate Chat repository.
- [x] Migrate Knowledge repository.
- [x] Migrate Workflow repositories.
- [x] Migrate Evaluation repository.
- [x] Migrate Runtime Policy repository.
- [x] Migrate Runtime Lab repository.
- [x] Migrate Customer Assistant repository.
- [x] Migrate Audit/Handoff repositories.
- [x] Run SQLite unit gate to preserve local path.
- [x] Run MySQL8 repository integration gate.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/060.2-returning-compat/`.

## 060.3 MySQL8 Alembic

- [x] RED: `alembic upgrade head` fails on clean MySQL8 before fixes.
- [x] Add MySQL8 DSN doc/example.
- [x] Add MySQL8 Docker/local startup doc.
- [x] Make baseline schema MySQL8-safe.
- [x] Make migrations `0001` through head MySQL8-safe.
- [x] Prevent MySQL8 from creating pgvector-only vector columns/indexes.
- [x] Move unsafe JSON defaults to app layer.
- [x] Verify PK autoincrement under MySQL8.
- [x] Verify indexes under `utf8mb4`.
- [x] Generate `schema-mysql8.sql`.
- [x] Run `alembic upgrade head` on real MySQL8.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/060.3-mysql8-alembic/`.

## 060.4 Weaviate Vector Store

- [x] RED: MySQL8 semantic retrieval fails without Weaviate path.
- [x] Document `HIFY_VECTOR_STORE=weaviate`.
- [x] Document `HIFY_WEAVIATE_URL`.
- [x] Decide Weaviate schema auto-create vs script-create.
- [x] Ensure document chunk embeddings upsert to Weaviate.
- [x] Ensure FAQ embeddings upsert to Weaviate.
- [x] Ensure document deletion removes/deactivates vectors.
- [x] Ensure FAQ deletion removes/deactivates vectors.
- [x] Ensure document semantic search queries Weaviate.
- [x] Ensure FAQ semantic search queries Weaviate.
- [x] Ensure hybrid retrieval fuses MySQL keyword + Weaviate semantic results.
- [x] Define unavailable-Weaviate behavior.
- [x] Run live Weaviate integration/UAT.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/060.4-weaviate-vector-store/`.

## 060.5 MySQL8 Module Smoke

- [x] Health/readiness smoke.
- [x] Provider CRUD smoke.
- [x] MCP CRUD smoke.
- [x] Agent CRUD/version/publish smoke.
- [x] Chat session/message smoke.
- [x] Knowledge metadata/document/FAQ smoke.
- [x] Knowledge retrieval via Weaviate smoke.
- [x] Workflow create/save/run metadata smoke.
- [x] Chatflow create/save/run metadata smoke.
- [x] Evaluation set/evaluator/experiment/report smoke.
- [x] Runtime Policy profile/release/decision smoke.
- [x] Customer Assistant session/run/task/event/action smoke.
- [x] Audit/Handoff smoke.
- [x] Frontend browser smoke against MySQL8-backed API.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/060.5-module-smoke/`.

## 060.6 Docs And Packaging

- [x] Add `.env.example.mysql8-weaviate`.
- [x] Add Docker Compose or equivalent startup doc.
- [x] Add DB init doc: `alembic upgrade head`.
- [x] Add Weaviate init doc.
- [x] Add known limits doc.
- [x] Update integration packaging docs for MySQL8 + Weaviate mode.
- [x] Save evidence under `artifacts/slices/060-mysql8-weaviate-demo-migration/final-gate/`.

## Final Acceptance

- [x] MySQL8 `alembic upgrade head` passes.
- [x] MySQL8 DDL artifact exists.
- [x] No MySQL8 migration creates pgvector-only vector columns/indexes.
- [x] Required repository write flows work without exposed `RETURNING`.
- [x] Weaviate document semantic retrieval passes.
- [x] Weaviate FAQ semantic retrieval passes.
- [x] Hybrid retrieval works with MySQL keyword + Weaviate semantic results.
- [x] Core module MySQL8 smoke tests pass.
- [x] Frontend browser smoke passes.
- [x] SQLite local path remains usable or deviations documented.
- [x] Docs explain startup/env/init/limits.
