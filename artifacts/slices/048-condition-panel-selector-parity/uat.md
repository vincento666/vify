# 048 Condition Panel Selector Parity UAT

Date: 2026-06-08

Target: `http://127.0.0.1:5173/workflows/4685/canvas`

Checks:

- Opened the current workflow canvas in the in-app browser.
- Selected the condition/selector node `router`.
- Verified the config panel visibly renders semantic branch names: `VIP 客户` and `普通客户`.
- Verified branch names are rendered as title buttons, not always-on text inputs.
- Clicked the first branch title, edited it to `VIP 客户 UAT`, and confirmed the new name appeared in both the config panel and node card.
- Restored the branch name to `VIP 客户`.
- Verified the final panel does not show generic `输入参数`/`输出参数` sections or generic `全部满足`/`任一满足` logic selectors.

Evidence:

- Screenshot: `artifacts/slices/048-condition-panel-selector-parity/screenshots/browser-uat-condition-panel.png`
- Final browser-observed node text: `选择器_1如果VIP 客户否则普通客户`
