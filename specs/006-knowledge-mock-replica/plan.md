# Plan 006: Knowledge Mock Replica

## Architecture

- `knowledge_base` and `document` tables are real SQLAlchemy models.
- Chunks may be stored in an in-process mock repository for this spec, matching
  current Java behavior.
- The public `KnowledgeFacade.search_chunks()` is the only API used by chat and
  workflow.

## Slice Order

006.1 -> 006.2 -> 006.3 -> 006.4
