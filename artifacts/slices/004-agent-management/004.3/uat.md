# 004.3 Agent Tool Binding UAT

Date: 2026-05-31

## Scope

- Create an Agent from the real frontend `/agent` page.
- Load enabled MCP servers into the tool binding tab.
- Select one MCP server during create.
- Reopen the Agent edit dialog and verify the selected tool remains checked.
- Verify browser-side API detail returns the persisted `toolIds`.

## Seed Data

- Provider: `UAT Provider 0043`
- Model: `UAT Model 0043`
- MCP servers:
  - `UAT Tool Alpha 0043`
  - `UAT Tool Beta 0043`

## Result

- Browser UAT: passed.
- Created Agent: `UAT Agent Tool 0043 1780231915174`
- Persisted `toolIds`: `[1]`
- Screenshot: `output/playwright/0043-agent-tool-binding.png`

## Gate Evidence

- RED integration: `artifacts/slices/004-agent-management/004.3/red.txt`
- RED unit: `artifacts/slices/004-agent-management/004.3/red-unit.txt`
- Focused backend tests: `artifacts/slices/004-agent-management/004.3/backend-focused.txt`
- MCP list support test: `artifacts/slices/004-agent-management/004.3/mcp-list.txt`
- Ruff: `artifacts/slices/004-agent-management/004.3/ruff.txt`
- Mypy: `artifacts/slices/004-agent-management/004.3/mypy.txt`
- Frontend unit: `artifacts/slices/004-agent-management/004.3/frontend-unit.txt`
- Frontend build: `artifacts/slices/004-agent-management/004.3/frontend-build.txt`
