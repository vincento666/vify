# 049 Condition Panel Section Action UAT

Date: 2026-06-08

Target: `http://127.0.0.1:5173/workflows/4685/canvas`

Checks:

- Reloaded the current workflow canvas in the in-app browser.
- Selected the `router` condition node.
- Verified the `条件分支` section text contains `条件分支` only once.
- Verified the add-branch action is an icon button in the section header.
- Verified the condition editor no longer renders a duplicate bottom `添加条件分支` text button.
- Clicked the header add button and confirmed it added one new branch while keeping the section title single.
- Removed the temporary branch after the UAT check to restore the current workflow page.

Evidence:

- Screenshot: `artifacts/slices/049-condition-panel-section-action/screenshots/browser-uat-condition-section-action.png`
- Browser-observed pre-check: title occurrences `1`, bottom add button count `0`, branch card count `1`.
- Browser-observed add-check: branch card count changed from `1` to `2`, title occurrences remained `1`.
