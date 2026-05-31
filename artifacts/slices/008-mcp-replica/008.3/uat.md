# 008.3 Browser UAT

- Date: 2026-05-31
- Slice: 008.3 Debug tool
- URL: http://127.0.0.1:5193/mcp/80/debug
- Screenshot: `output/playwright/0083-mcp-debug.png`

## Flow

1. Created an MCP Server with endpoint `mock://tools`.
2. Opened its debug page.
3. Selected `lookup_order`.
4. Filled `orderId=A-100`.
5. Clicked `执行调用`.

## Expected Result

- The result history shows `Order A-100 status: SHIPPED`.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
