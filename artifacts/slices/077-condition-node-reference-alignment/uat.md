# UAT And Reference Evidence

## Official / Source References

- AgentArts judgment node manual: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0066.html
- AgentArts condition UI image captured from official manual: `screenshots/agentarts-condition-reference.png`
- Coze Studio source reference:
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/form-extensions/setters/condition/multi-condition/condition-params-item/index.tsx`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/form-extensions/setters/condition/multi-condition/condition-params-item/utils.ts`

## Hify Browser Evidence

- Before/current mismatch screenshot: `screenshots/hify-condition-current.png`
- After fix screenshot: `screenshots/hify-condition-after.png`

## Layout Finding

Coze's condition row uses a fixed operator column on the left, while the left variable selector and right value/value-expression input stack in the main column. Hify previously placed the operator to the right of the left variable selector, so the condition form felt unlike the Coze/AgentArts pattern and forced users to scan across a broken row.

## Implemented Check

`frontend/e2e/workflow-condition-branch-values.mjs` now verifies the condition row geometry directly:
- operator x-position is before the variable selector
- left variable selector and right value input share the same main-column x-position
