# 008.4 Browser UAT

- Date: 2026-05-31
- Slice: 008.4 Chat fallback compatibility
- URL: http://127.0.0.1:5193/chat
- Screenshot: `output/playwright/0084-chat-mcp-fallback.png`

## Flow

1. Seeded a mock model config.
2. Created an MCP Server with endpoint `mock://tools`.
3. Created an Agent bound to that MCP server.
4. Opened the chat page.
5. Sent `please use tool`.

## Expected Result

- The assistant message includes `Tool mock (lookup_order, refund_order): please use tool`.
- The existing non-MCP tool fallback remains compatible.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
