# Spec 009: Real RAG pgvector

## Goal

Replace the knowledge mock with real document parsing, chunk storage, embedding,
and PostgreSQL pgvector similarity search while preserving public API behavior.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 009.1 Vector schema | Alembic creates chunk/embedding tables and pgvector index | RED: schema test fails; Unit: vector model; Integration: pgvector migration; E2E: N/A; UAT: DB inspect note |
| 009.2 Document parser | txt/md/pdf parsing produces normalized chunks | RED: parser fixtures fail; Unit: parser; Integration: upload pipeline; E2E: document chunks; UAT: chunks visible |
| 009.3 Embedding pipeline | DONE document has embeddings stored in pgvector | RED: fake embedding test fails; Unit: batcher; Integration: pgvector insert; E2E: status flow; UAT: DONE with chunk count |
| 009.4 Similarity search | `search_chunks` returns nearest chunks by cosine distance | RED: vector search test fails; Unit: ranking adapter; Integration: pgvector query; E2E: RAG chat; UAT: answer uses relevant docs |
| 009.5 Operational hardening | Reprocessing, failure, timeout, and observability are covered | RED: failure tests fail; Unit: state machine; Integration: retry/fail rows; E2E: failure display; UAT: user sees recoverable state |

## Compatibility Rules

- Public knowledge APIs remain compatible with `006`.
- The mock implementation may remain as test/dev fallback, but production path
  uses pgvector.
