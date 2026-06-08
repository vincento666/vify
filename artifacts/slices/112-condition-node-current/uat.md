# 112 Condition Node Current Gate

## RED Context

- 用户指出条件/选择器节点应是特制节点：卡片显示语义分支名，配置面板只有条件分支块，不应暴露通用输入/输出；比较符、左右变量引用和分支名编辑必须对齐 Coze-like 使用心智。
- 本轮未改产品代码，先用现有专项 E2E/集成/浏览器 UAT 验证当前实现。

## GREEN

- `e2e-condition-branch-endpoints.txt`: 条件卡片显示分支名、端点垂直居中对齐分支块、分支 header 点击编辑、section header 添加分支通过。
- `e2e-workflow-canvas-ux-lifecycle.txt`: 多条件分支与复杂 chatflow 指引分支路径通过。
- `integration-unit-condition.txt`: 后端条件运行、变量右值比较、长度/空值操作符、runtime parity 通过。
- `unit.txt`: nodeConfig / flowGraph / rem closure 通过。

## Browser UAT

- URL: `http://127.0.0.1:5173/workflows/7871/canvas`
- 卡片：显示 `VIP 客户` / `普通客户` 等分支语义，不显示泛化输入/输出。
- 面板：显示“连接多个下游分支”说明；分支标题点击进入编辑态；两条条件行均有比较符、左值变量按钮、右值变量按钮。
- 截图：`screenshots/browser-uat-condition-panel.png`
- UAT 后恢复内置浏览器到 `http://127.0.0.1:5173/workflows/6217/canvas`。
