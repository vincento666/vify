# 007.1 Browser UAT

- Date: 2026-05-31
- Slice: 007.1 Workflow CRUD
- URL: http://127.0.0.1:5193/workflows
- Screenshot: `output/playwright/0071-workflow-crud.png`

## Flow

1. Opened `/workflows/create`.
2. Entered a unique workflow name.
3. Kept the default workflow JSON example.
4. Submitted the workflow.
5. Returned to the workflow list.
6. Opened the detail drawer.

## Expected Result

- The created workflow appears in the list.
- The detail drawer shows `节点 (7)`.
- The detail drawer shows `连线 (8)`.
- The graph contains the `classify` node.

## Gate Result

- RED observed before implementation.
- Backend unittest: passed.
- Ruff: passed.
- Mypy: passed.
- Frontend unit test: passed.
- Frontend build: passed.
- Browser UAT: passed.
