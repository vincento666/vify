# 006.4 Browser UAT

- Date: 2026-05-31
- Slice: 006.4 Mock search
- URL: http://127.0.0.1:5193/chat
- Fixture: `artifacts/slices/006-knowledge-mock-replica/006.3/chunk-guide.txt`
- Screenshot: `output/playwright/0064-rag-references.png`

## Flow

1. Seeded a model config for the test Agent.
2. Created a knowledge base through the running API.
3. Uploaded `chunk-guide.txt` through the running API so chunks are stored in the uvicorn process.
4. Created a knowledge-bound Agent and chat session.
5. Opened the Chat page in a browser.
6. Sent `reset password`.

## Expected Result

- The assistant stream contains `RAG mock: reset password`.
- The assistant stream contains `References:`.
- The assistant stream includes the matched chunk `How to reset password`.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
