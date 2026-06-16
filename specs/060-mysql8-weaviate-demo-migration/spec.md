# Spec 060: MySQL8 + Weaviate Demo Migration

## Goal

Migrate the current Hify demo to a MySQL8 primary database and use Weaviate as
the external vector store for semantic retrieval.

This is a demo migration spec, not a production live-data migration. The target
is to make the current project run cleanly on MySQL8 for business persistence
while keeping vector retrieval outside MySQL.

Target shape:

```text
FastAPI backend
  -> MySQL8 / InnoDB
       provider / agent / chat / workflow / chatflow / evaluation /
       runtime policy / customer assistant / audit / handoff / knowledge metadata

  -> Weaviate
       document chunk embeddings
       FAQ embeddings
       semantic vector search

  -> application/domain layer
       keyword recall
       FAQ exact/heuristic recall
       hybrid RRF/rerank fusion
```

## Current State

Current DB behavior:

```text
Default DB URL: sqlite:///./hify.db
Alembic default URL: sqlite:///./hify.db
Primary local test DB: SQLite
Vector-capable relational path: PostgreSQL + pgvector
MySQL dependency: PyMySQL already present
Full MySQL8 compatibility: not implemented
```

Important coupling:

```text
app/core/schema.py
  imports pgvector.sqlalchemy.Vector
  defines document_embedding.embedding as Vector(1536)
  defines knowledge_faq_embedding.embedding as Vector(1536)
  defines PostgreSQL ivfflat/vector_cosine_ops indexes

app/modules/knowledge/infra/repository.py
  PostgreSQL path uses pgvector <=> distance SQL
  non-PostgreSQL path falls back to in-memory cosine

repositories
  many create/update flows use .returning()
  MySQL8 cannot rely on PostgreSQL RETURNING semantics
```

## Decision

Use:

```text
Primary business DB: MySQL8
Vector DB: Weaviate
```

Do not use:

```text
MySQL8 as native vector search engine
PostgreSQL kept only for pgvector
App-only in-memory vector search as normal semantic path
```

Rationale:

- MySQL8 fits host/demo business persistence needs.
- Current vector model is pgvector-specific and not MySQL8-compatible.
- 035 already introduced vector-store adapter direction and Weaviate support.
- Weaviate keeps semantic search decoupled from relational DB choice.

## Scope

In scope:

- MySQL8 demo runtime configuration;
- MySQL8-safe Alembic migration path;
- repository write compatibility without hard `.returning()` dependency;
- MySQL8-safe SQLAlchemy metadata;
- Weaviate vector-store path for document chunks and FAQ embeddings;
- MySQL8 + Weaviate smoke/integration/UAT evidence;
- docs for Windows/Docker startup, DB init, vector init, known limits.

Out of scope:

- production live-data migration;
- zero-downtime cutover;
- dual-write;
- cross-DB data backfill automation;
- MySQL-native vector search;
- Weaviate HA/backup/cluster ops;
- frontend route/UI redesign;
- API response contract changes.

## Target Architecture

```text
               +----------------------+
               |      FastAPI app     |
               +----------+-----------+
                          |
          +---------------+----------------+
          |                                |
          v                                v
+--------------------+          +----------------------+
| SQLAlchemy repos   |          | VectorStoreAdapter   |
+---------+----------+          +----------+-----------+
          |                                |
          v                                v
+--------------------+          +----------------------+
| MySQL8 / InnoDB    |          | Weaviate             |
| business state     |          | embeddings/search    |
+--------------------+          +----------------------+
```

Module responsibility:

```text
app/core/database.py
  engine/session/bootstrap, dialect-aware safe init

app/core/schema.py
  relational metadata; MySQL8 must not require pgvector-only Vector/indexes

app/modules/*/infra/repository.py
  DB reads/writes; no caller-visible RETURNING dependency

app/modules/knowledge/domain/vector_store.py
  Weaviate selection/config and vector-store boundary

app/modules/knowledge/infra/repository.py
  MySQL metadata/chunks/FAQ rows; no MySQL pgvector SQL
```

## Data Ownership

MySQL8 owns:

```text
provider
model_config
provider_health
mcp_server
agent
agent_tool
agent_version
agent_publish_record
agent_prompt_optimization
chat_session
chat_message
knowledge_base
document
document_chunk
knowledge_faq
workflow / workflow_node / workflow_edge / workflow_run / workflow_node_run
chatflow state/channel/version tables
api_resource / api_tool
evaluation tables
runtime_policy tables
customer_assistant tables
handoff_ticket
audit_log
```

Weaviate owns:

```text
document chunk vectors
FAQ vectors
vector metadata:
  knowledgeBaseId
  documentId
  chunkId
  faqId
  embeddingModel
  content/question snapshot
```

MySQL8 may keep vector metadata for UI/debug if needed, but MySQL8 must not
require pgvector `Vector` columns.

## Compatibility Requirements

### MySQL8

Minimum:

```text
MySQL: 8.0.x
Engine: InnoDB
Charset: utf8mb4
Collation: utf8mb4_0900_ai_ci or host-standard utf8mb4 collation
Driver: mysql+pymysql
```

Demo DSN:

```text
HIFY_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4
```

### Weaviate

Demo config:

```text
HIFY_VECTOR_STORE=weaviate
HIFY_WEAVIATE_URL=http://127.0.0.1:8080
HIFY_WEAVIATE_API_KEY=optional
```

Embedding provider may remain fake/local for deterministic demo, unless a later
task enables live external embeddings.

### JSON

Rules:

- `sa.JSON()` may map to MySQL JSON;
- app code supplies JSON defaults;
- avoid DB server defaults for JSON;
- no PostgreSQL JSON operators in MySQL path.

### Boolean

Rules:

- SQLAlchemy boolean maps to MySQL `TINYINT(1)`;
- API output remains Python boolean.

### RETURNING

MySQL8 path must not require:

```text
insert(...).returning(...)
update(...).returning(...)
```

Target pattern:

```text
insert/update
  -> flush/commit
  -> fetch by primary key or stable unique key
```

PostgreSQL may keep `RETURNING` only behind helper functions.

### Vector Tables

MySQL8 migration must not create:

```text
Vector(1536)
ivfflat index
vector_cosine_ops
embedding <=> query_vector SQL
```

## Functional Requirements

- FR-001: Backend starts with MySQL8 DSN.
- FR-002: `alembic upgrade head` passes on clean MySQL8.
- FR-003: MySQL8 schema has no pgvector-only columns/indexes.
- FR-004: App startup does not run PostgreSQL extension setup on MySQL8.
- FR-005: Repository create/update paths work without MySQL-incompatible
  `RETURNING`.
- FR-006: Provider CRUD works on MySQL8.
- FR-007: MCP CRUD works on MySQL8.
- FR-008: Agent CRUD/version/publish works on MySQL8.
- FR-009: Chat session/message persistence works on MySQL8.
- FR-010: Workflow and Chatflow metadata persistence works on MySQL8.
- FR-011: Knowledge base/document/chunk/FAQ metadata works on MySQL8.
- FR-012: Document semantic retrieval uses Weaviate in MySQL8 mode.
- FR-013: FAQ semantic retrieval uses Weaviate in MySQL8 mode.
- FR-014: Hybrid retrieval fuses MySQL keyword/FAQ signals with Weaviate
  semantic results.
- FR-015: Evaluation persistence works on MySQL8.
- FR-016: Runtime policy persistence works on MySQL8.
- FR-017: Customer assistant runtime persistence works on MySQL8.
- FR-018: Frontend behavior remains unchanged.

## Acceptance Criteria

- MySQL8 DSN documented and verified.
- Weaviate config documented and verified.
- MySQL8 Alembic clean upgrade passes.
- MySQL8 DDL artifact exists.
- MySQL8 schema contains no pgvector-only vector columns/indexes.
- All repository writes used by smoke flows work without exposed `RETURNING`.
- Knowledge document semantic retrieval works through Weaviate.
- Knowledge FAQ semantic retrieval works through Weaviate.
- Core module smoke suite passes on MySQL8.
- Browser smoke passes against MySQL8-backed backend.
- SQLite local path remains usable unless explicitly documented.
- Demo limitations documented.

## Risks

| Risk | Severity | Impact | Mitigation |
|---|---:|---|---|
| `.returning()` unsupported | High | create/update flows fail | write helper + MySQL tests |
| pgvector type/index unsupported | High | Alembic fails | skip/replace vector tables in MySQL path |
| Weaviate unavailable | Medium | semantic search unavailable | explicit health/error/degraded mode |
| JSON defaults | Medium | migration/runtime errors | app-layer defaults |
| utf8mb4 index length | Medium | DDL fails | real MySQL DDL gate |
| data drift MySQL/Weaviate | Medium | stale retrieval | idempotent upsert/delete + reconciliation test |

## Evidence Path

```text
artifacts/slices/060-mysql8-weaviate-demo-migration/
├── 060.1-dialect-inventory/
├── 060.2-returning-compat/
├── 060.3-mysql8-alembic/
├── 060.4-weaviate-vector-store/
├── 060.5-module-smoke/
└── final-gate/
```

## Completion Gate

060 complete only when:

- tasks.md final acceptance checked;
- MySQL8 Alembic evidence exists;
- Weaviate semantic retrieval evidence exists;
- core module MySQL8 smoke evidence exists;
- docs describe startup/env/init/limits;
- no frontend contract or API envelope regression.
