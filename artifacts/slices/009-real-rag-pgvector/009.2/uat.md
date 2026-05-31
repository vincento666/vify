# 009.2 Browser UAT

- Date: 2026-05-31
- Slice: 009.2 Document parser
- URL: http://127.0.0.1:5193/knowledge/139/documents
- Screenshot: `output/playwright/0092-normalized-chunks.png`

## Flow

1. Created a knowledge base.
2. Opened the document page in the browser.
3. Uploaded `0092-reset.md` through the upload dialog.
4. Waited for processing to complete.
5. Opened the chunk preview dialog.

## Expected Result

- The document reaches `DONE`.
- The chunk count is `2`.
- The visible chunks are normalized:
  - `Reset Guide`
  - `Reset password Contact support`
- Markdown markers such as `#` and `**support**` are not visible.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
