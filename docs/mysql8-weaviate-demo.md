# MySQL8 + Weaviate Demo Mode

Spec060 runs Hify with MySQL8 for business data and Weaviate for semantic
vectors.

## Start Dependencies

```bash
docker compose -f docker-compose.mysql8-weaviate.yml up -d
```

Use the demo environment:

```bash
cp .env.example.mysql8-weaviate .env.mysql8-weaviate
set -a
. ./.env.mysql8-weaviate
set +a
```

Initialize the database:

```bash
uv run alembic upgrade head
```

Seed optional RuntimeLab airline Chatflow demo data after migrating an empty
MySQL database:

```bash
PYTHONPATH=. uv run python scripts/seed_runtime_lab_airline_sops.py
```

The seed command writes fresh `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS` values for the
current database. Do not reuse IDs copied from a SQLite/Postgres `.env`; clear
the variable or rerun the seed after rebuilding the MySQL demo database.

Run the backend:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Runtime Ownership

MySQL8 owns relational state: provider, model config, MCP, agent, chat,
knowledge metadata, document chunks, FAQ rows, workflow/chatflow, evaluation,
runtime policy, customer assistant, audit, and handoff.

Weaviate owns semantic vectors:

```text
HifyDocumentChunk
HifyKnowledgeFaq
```

The app auto-creates Weaviate classes on first write/search. Document and FAQ
reprocessing uses replace semantics, and delete/disable paths remove external
vectors.

## Validation Commands

```bash
PYTHONPATH=. \
HIFY_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4 \
HIFY_VECTOR_STORE=weaviate \
HIFY_WEAVIATE_URL=http://127.0.0.1:8080 \
HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE=fake \
HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS= \
uv run pytest tests/contract tests/integration tests/e2e
```

For MySQL-specific repository coverage:

```bash
PYTHONPATH=. \
HIFY_MYSQL8_TEST_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3306/hify?charset=utf8mb4 \
uv run pytest tests/integration/mysql8
```

## Known Limits

- Demo migration only; no production live-data cutover or dual-write.
- MySQL8 does not create pgvector-only embedding tables or vector indexes.
- Semantic retrieval requires Weaviate when `HIFY_DATABASE_URL` points at MySQL.
- Weaviate vector dimensions are fixed per class after first insert; recreate
  demo classes if changing embedding dimensions.
- Runtime lab demo gates should set `HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE=fake`
  unless explicitly testing a live LLM route.
- Runtime lab Chatflow bindings are database-local IDs. After DB reset or
  migration, rerun the seed script or leave `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS`
  empty to use the mock SOP adapter.
