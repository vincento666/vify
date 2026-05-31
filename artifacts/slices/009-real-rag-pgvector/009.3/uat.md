# 009.3 Browser UAT

- Date: 2026-05-31
- Slice: 009.3 Embedding pipeline
- URL: http://127.0.0.1:5193/knowledge/156/documents
- Screenshot: `output/playwright/0093-done-with-embeddings.png`

## Flow

1. Created a knowledge base.
2. Uploaded a TXT document through the browser.
3. Waited for processing to complete.
4. Inspected embedding rows for the uploaded document.

## Expected Result

- The document reaches `DONE`.
- The document shows chunk count `2`.
- `document_embedding` contains one row per chunk.
- Each embedding uses model `fake-local-hash-v1` and dimension `1536`.

## Observed Embedding State

```json
{
  "count": 2,
  "dimensions": [
    1536,
    1536
  ],
  "models": [
    "fake-local-hash-v1",
    "fake-local-hash-v1"
  ]
}
```

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
