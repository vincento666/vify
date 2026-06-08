# UAT And Reference Evidence

## Reference Basis

- Coze Studio condition operator source:
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/form-extensions/setters/condition/multi-condition/condition-params-item/operator/index.tsx`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/form-extensions/setters/condition/multi-condition/condition-params-item/constants.ts`
  - `artifacts/research/coze-studio/frontend/packages/workflow/playground/src/form-extensions/setters/condition/multi-condition/condition-params-item/utils.ts`
- AgentArts judgment node manual previously captured in 077: https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0066.html

## Browser Evidence

- Screenshot: `screenshots/condition-operator-type-semantics.png`

## Verified Behaviors

- A string left variable shows length comparison options instead of numeric greater/less labels.
- Empty-check operators do not require a right value and disable the right value picker.
