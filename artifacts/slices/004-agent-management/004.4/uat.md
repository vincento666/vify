# 004.4 Agent Knowledge/Workflow Binding UAT

Date: 2026-05-31

## Scope

- Create an Agent from the real frontend `/agent` page.
- Load knowledge base and workflow options into the Agent ability binding tab.
- Select one knowledge base and one workflow during create.
- Verify the Agent list shows both `知识库` and `工作流` tags.
- Reopen edit dialog and verify both selected values remain visible.
- Verify browser-side API detail returns `knowledgeBaseId` and `workflowId`.

## Seed Data

- Provider: `UAT Provider 0044`
- Model: `UAT Model 0044`
- Knowledge base: `UAT KB 0044`
- Workflow: `UAT Workflow 0044`

## Result

- Browser UAT: passed.
- Created Agent: `UAT Agent Binding 0044 1780232466833`
- Persisted `knowledgeBaseId`: `1`
- Persisted `workflowId`: `1`
- Screenshot: `output/playwright/0044-agent-ability-binding.png`

## Gate Evidence

- RED: `artifacts/slices/004-agent-management/004.4/red.txt`
- Binding option RED: `artifacts/slices/004-agent-management/004.4/options-red.txt`
- Focused backend tests: `artifacts/slices/004-agent-management/004.4/focused.txt`
- Binding option tests: `artifacts/slices/004-agent-management/004.4/options.txt`
- Ruff: `artifacts/slices/004-agent-management/004.4/ruff.txt`
- Mypy: `artifacts/slices/004-agent-management/004.4/mypy.txt`
- Frontend unit: `artifacts/slices/004-agent-management/004.4/frontend-unit.txt`
- Frontend build: `artifacts/slices/004-agent-management/004.4/frontend-build.txt`
