# 096 Endpoint Affordance Current Rerun

## RED

- `e2e-endpoint-connection-radius-current-rerun.txt`: 旧脚本仍按 `42px/44px` 过大磁吸半径断言，并用 hitbox 宽度计算倍率；当前产品设计保持 hitbox 不变，只放大端点圆点，因此失败。

## GREEN

- `e2e-endpoint-connection-radius-after-rebaseline.txt`: 连接拖拽靠近目标端点时，读取 `::after` 圆点 scale，确认 3x。
- `e2e-endpoint-affordances-current-rerun.txt`: 节点 hover 2x、端点 hover 3x、选中节点 1.2x、左右端点中心贴边回归通过。
- `e2e-condition-branch-endpoints-current-rerun.txt`: 条件分支端点垂直居中对齐对应分支块，分支改名后端点标签同步。
- `unit-endpoint-after-rebaseline.txt`: canvas controls、rem governance、rem closure 通过。

## Browser UAT

- URL: `http://127.0.0.1:5173/workflows/6217/canvas`
- 结果：start 卡片 source 端点中心贴近卡片右边缘，纵向中心与卡片中心一致；当前页面截图保存到 `screenshots/browser-uat-endpoint-current.png`。
- 说明：内置浏览器 CUA hover 在本会话不稳定，hover/drag 动画倍率由 Playwright E2E 做自动化验收。
