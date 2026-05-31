# 010.4 Browser UAT

- Date: 2026-05-31
- Slice: 010.4 Second LLM round
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0104-two-round-tool-chat.png`

## Flow

1. Created an MCP server with endpoint `mock://tools`.
2. Created an Agent bound to that MCP server.
3. Opened the chat page.
4. Sent `where is order A-100?`.

## Expected Result

- The assistant response is produced by the second LLM round.
- The response includes `Tool answer:`.
- The response includes `Order A-100 status: SHIPPED`.
- The old `Tool mock: ...` fallback is not used for this order query.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
