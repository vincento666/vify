# 006.3 Browser UAT

- Date: 2026-05-31
- Slice: 006.3 Mock chunk pipeline
- URL: http://127.0.0.1:5193/knowledge/16/documents
- Fixture: `artifacts/slices/006-knowledge-mock-replica/006.3/chunk-guide.txt`
- Screenshot: `output/playwright/0063-document-chunks.png`

## Flow

1. Created a knowledge base from the browser UI.
2. Opened the document list page.
3. Uploaded `chunk-guide.txt`.
4. Waited for document status to become `已完成`.
5. Opened `查看分块`.

## Expected Result

- The uploaded document becomes `DONE`.
- The table shows a chunk count of `3`.
- The chunk preview dialog renders:
  - `Intro`
  - `How to reset password`
  - `How to contact support`

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
