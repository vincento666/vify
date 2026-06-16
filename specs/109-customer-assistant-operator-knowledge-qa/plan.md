# Plan: 109.1 Operator Knowledge Q&A

## Design

Add a read-only service method that:

1. Loads the session through the existing tenant-aware `_ensure_session` path.
2. Reads current task rows, proposed-action rows, recent events, and sanitized
   session context.
3. Uses `KnowledgeFacade.search_context` against session `knowledgeBaseIds`.
4. Builds deterministic answer text from the best FAQ/knowledge hit and a
   compact ledger summary.
5. Returns `answer`, `sources`, `evidence`, `contextSummary`, and `warnings`
   without writing runs, events, tasks, or proposed actions.

## API

`POST /api/v1/customer-assistant/sessions/{session_id}/operator-knowledge-qa`

Request:

```json
{
  "question": "退票和行李额可以并行处理吗？"
}
```

Response envelope remains `{code, message, data}`.

## Verification

- Capture RED from the new integration test before implementation.
- Run the focused integration test after implementation.
- Run existing nearby customer-assistant unit/integration tests for advisory
  knowledge and demo story behavior.
- Run ruff on touched backend/test files.
