# 028 Workflow/Chatflow Input Picker Model Hardening

## Summary

修复工作流/对话流右侧配置面板中变量引用输入、变量选择器、LLM 模型选择与模型参数面板的高保真问题。

## Requirements

- 可引用变量的输入框输入 `{` 时自动补全为 `{{}}`，光标位于中间，变量选择器打开。
- 用户可以用 Backspace/Delete 删除补全符号，也可以按 `Esc` 关闭变量选择器继续手动输入。
- 变量选择器重构为 Coze/vifly-experiment 风格：在右侧配置面板内操作时向左侧展开，带搜索、分组源列表、二级变量列表、轻量卡片样式，且不沿用旧版紧凑控件视觉。
- LLM 模型选择器提供真实搜索输入和搜索按钮，按模型名/供应商/说明过滤。
- LLM 模型参数面板中的数值项提供长条滑轨、圆点滑块和右侧可编辑/可微调数值输入框。

## Acceptance

- 每个 slice 先保存红测输出，再实现并跑对应单测/e2e。
- 涉及前端视觉尺寸时通过 `remScaleClosure`。
- 使用浏览器 UAT 验证 chatflow/workflow 画布右侧配置面板，并保存截图。
