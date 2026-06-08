# 045 Condition Branch Endpoints UAT

Date: 2026-06-08

Target: http://127.0.0.1:5173/workflows/4685/canvas

Checks:

- Opened the workflow canvas in the in-app browser.
- Verified selector node card renders branch blocks instead of generic input/output rows.
- Verified card shows `如果 VIP 客户` and `否则 普通客户`.
- Clicked the selector node and verified the config header keeps the selector title plus the priority-branch explanation.
- Added a new condition branch.
- Edited the new branch header name to `高价值订单`.
- Verified the selector card updated to `否则如果 高价值订单`.
- Verified right-side condition source labels updated to `VIP 客户`, `高价值订单`, and `普通客户`.

Screenshot:

- `screenshots/browser-uat-selector-node.png`
