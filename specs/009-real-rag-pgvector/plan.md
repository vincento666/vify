# Plan 009: Real RAG pgvector

## Architecture

- Add chunk and embedding ORM models.
- Use PostgreSQL + pgvector for vector storage.
- Keep embedding provider behind an interface and fake it in tests.
- Avoid long-running parsing/embedding inside request handlers.

## Slice Order

009.1 -> 009.2 -> 009.3 -> 009.4 -> 009.5
