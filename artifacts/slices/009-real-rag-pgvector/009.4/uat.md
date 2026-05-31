# 009.4 Browser UAT

- Date: 2026-05-31
- Slice: 009.4 Similarity search
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0094-vector-rag-chat.png`

## Flow

1. Created a knowledge base with three chunks.
2. Created an Agent bound to that knowledge base.
3. Opened the chat page.
4. Sent `reset password`.

## Expected Result

- The assistant response includes `References:`.
- The first reference is `How to reset password`.
- Less relevant chunks remain lower in the reference list.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
