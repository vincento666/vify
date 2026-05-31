# 008.1 Browser UAT

- Date: 2026-05-31
- Slice: 008.1 MCP Server CRUD
- URL: http://127.0.0.1:5193/mcp
- Screenshot: `output/playwright/0081-mcp-crud.png`

## Flow

1. Opened the MCP Server list page.
2. Created a Server with a unique name and `mock://tools` endpoint.
3. Edited the Server endpoint to `mock://tools-v2`.
4. Deleted the Server and verified it disappeared from the list.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
