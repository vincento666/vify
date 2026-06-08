# 051 Condition Branch Values Regression

Date: 2026-06-08

Scope:

- Add an E2E regression for the condition/selector node value row and variable picker behavior.
- This is a test-only slice that records already-implemented behavior so future UI polish does not regress it.

Checks:

- Condition rows do not expose the old explicit `引用` / `字面量` mode copy.
- Typing `{` into a condition value auto-completes to `{{}}`.
- The condition variable picker only shows connected upstream node sources for this local condition context.
- Unused static groups such as `用户变量`、`应用变量`、`会话变量`、`系统变量`、`用户画像` are hidden in this picker.
- Selecting `开始.intent` stores `{{start.intent}}` and renders as a variable chip.
- `添加条件` uses an icon.
- `添加条件分支` lives in the section header and the editor body does not render a duplicate bottom add button.

Gates:

- E2E: `workflow-condition-branch-values.mjs`
- Focused unit/rem: `nodeConfig.test.ts`, `variableCatalog.test.ts`, `remScaleClosure.test.ts`
- Full frontend unit
- Frontend build

Evidence:

- Screenshot: `artifacts/slices/051-condition-branch-values-regression/screenshots/e2e-condition-branch-values.png`
