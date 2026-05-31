# 009.5 Browser UAT

- Date: 2026-05-31
- Slice: 009.5 Operational hardening
- URL: http://127.0.0.1:5193/knowledge/194/documents
- Screenshot: `output/playwright/0095-failed-empty-document.png`

## Flow

1. Created a knowledge base.
2. Uploaded an empty TXT document through the browser.
3. Waited for processing to finish.
4. Verified detail and chunk APIs.

## Expected Result

- The document reaches `FAILED`.
- The row remains visible and deletable.
- The detail API exposes `Document is empty`.
- The chunks API returns an empty list.

## Observed State

```json
{
  "status": "FAILED",
  "errorMessage": "Document is empty",
  "chunkCount": 0
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
