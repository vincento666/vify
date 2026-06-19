# 209.1 Customer Assistant Tabbed Shell

## 修改范围
- `frontend/src/views/customerAssistant/CustomerAssistantPanel.vue`
- `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
- `frontend/src/views/customerAssistant/customerAssistantViewModel.ts`
- `frontend/src/views/customerAssistant/customerAssistantViewModel.test.ts`

## 红测证据
- `red.txt`: tabbed shell、三列 compact 布局初始红测。
- `red-one-screen-scroll.txt`: 一屏高度与列内滚动初始红测。
- `red-equal-height.txt`: 中间列未吃满高度初始红测。
- `red-operator-workbench-boundary.txt`: 坐席窗口与助手工作台职责混用初始红测。
- `red-operator-lane-passenger-dialogue-label.txt`: 中间坐席窗口残留 Assistant 标签初始红测。

## 实现摘要
- 左侧改为“会话/故事”tab，压缩多客户会话四个指标为单行。
- 中间改为“旅客/坐席”tab，坐席窗口只模拟发给旅客的话术，不再承载追问助手。
- 右侧改为“助手/任务/证据/审计”tab，助手 tab 承载追问助手、运行事件回显和坐席提示。
- 外层 shell 固定一屏高度，三列等高，超出内容在对应列内部滚动。
- View model 不再把 `operatorRecommendation` 混入中间坐席消息流，AI 建议留在右侧工作台。

## 已跑门禁
- Focused frontend unit: `frontend-focused-final.txt`
- Frontend remScaleClosure: `frontend-rem-final.txt`
- Diff unit scan: `frontend-px-scan-final.txt`
- Full frontend unit: `frontend-full-unit-final.txt`
- Frontend build: `frontend-build-final.txt`
- Browser UAT: `inapp-browser-final-operator-workbench-boundary.txt`
- Compact browser UAT refresh: `inapp-browser-compact-tabbed-shell-uat.txt`

## 剩余风险
- 715px 宽视口下三列保留会让右侧工作台较窄，但当前验收要求优先保证三列不折叠、一屏高度和列内滚动。
