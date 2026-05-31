# 008.2 Browser UAT

- Date: 2026-05-31
- Slice: 008.2 Connection and tools
- URL: http://127.0.0.1:5193/mcp/68/debug
- Screenshot: `output/playwright/0082-mcp-tools.png`

## Flow

1. Created an MCP Server with endpoint `mock://tools`.
2. Opened the MCP Server list page.
3. Clicked `测试`.
4. Verified the drawer showed connection success and `lookup_order`.
5. Opened the debug page.
6. Verified `lookup_order` and its `orderId` parameter were visible.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
