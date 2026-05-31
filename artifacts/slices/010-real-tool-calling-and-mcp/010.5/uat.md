# 010.5 Browser UAT

- Date: 2026-05-31
- Slice: 010.5 Production hardening
- URL: http://127.0.0.1:5193/mcp/216/debug
- Screenshot: `output/playwright/0105-tool-error.png`

## Flow

1. Created an MCP server with endpoint `mock://tools`.
2. Opened the MCP debug page.
3. Selected `lookup_order`.
4. Switched to JSON mode.
5. Submitted `{}`.

## Expected Result

- The page shows a failed call record.
- The error message is `orderId is required`.
- The result is clearly distinguishable from a successful tool result.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
