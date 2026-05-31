# Spec 006: Knowledge Mock Replica

## Goal

Replicate the current knowledge-base behavior exactly: knowledge-base CRUD,
document upload, mock chunking, mock search, and chat integration hook.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 006.1 Knowledge-base CRUD | User can create/list/detail/update/delete knowledge bases | RED: route contract fails; Unit: schema; Integration: DB; E2E: KB page; UAT: CRUD works |
| 006.2 Document upload | User can upload txt/md/pdf and see document state | RED: upload contract fails; Unit: file validation; Integration: multipart route; E2E: document page; UAT: upload visible |
| 006.3 Mock chunk pipeline | Uploaded document becomes DONE with chunks | RED: processing test fails; Unit: chunk splitter; Integration: task status; E2E: chunks page; UAT: chunks visible |
| 006.4 Mock search | Chat/workflow can retrieve topK chunks from mock store | RED: search test fails; Unit: deterministic topK; Integration: service facade; E2E: RAG chat path; UAT: answer includes reference behavior |

## Compatibility Rules

- PDF remains mock placeholder in this spec.
- No embeddings or pgvector are introduced here.
- Mock search may be deterministic but must preserve current user-visible topK
  behavior.
