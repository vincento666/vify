# 110 Chatflow Start/End/Trial Regression UAT

## RED

- `e2e-chatflow-end-output-editor.txt`: END 输出变量 picker 仍暴露旧默认 `USER_INPUT`，没有 `start.sys.query`。
- `e2e-chatflow-node-test.txt`: 单节点试运行误触真实 LLM 路径，等待运行结果超时。
- `e2e-chatflow-node-test-after-fix.txt`: 切到 MESSAGE 节点后仍保留 LLM 会话历史断言，夹带了错误验收点。
- `red-inline-end-answer.txt`: END 回答内容 `{{` inline picker 只看本地输出变量，缺少上游 `start.sys.query`。
- Browser UAT 初次检查失败：END 回答内容 inline picker 只显示 `output / String`，与 END 作为最终渲染模板可引用上游变量的产品语义不符。

## GREEN

- `unit-variable-catalog-inline-end.txt`: 10 tests passed, END inline catalog 已走上游变量目录。
- `unit-frontend-rem-final.txt`: 5 files / 57 tests passed，包含 rem 门禁。
- `full-unit.txt`: 58 files / 211 tests passed。
- `integration-chatflow-start-end.txt`: 9 integration tests passed，覆盖 chatflow 变量注入、空 END 输出不 500、Fake LLM 流式事件。
- `build.txt`: `vue-tsc && vite build` passed。
- `e2e-chatflow-start-panel-parity.txt`: START 面板变量名/类型/必填回归通过。
- `e2e-chatflow-end-panel-parity.txt`: END 面板返回模式/回答内容/输出结构回归通过。
- `e2e-chatflow-end-output-editor-after-inline-fix.txt`: END 输出变量值和回答内容 inline picker 均可引用 `start.sys.query`。
- `e2e-workflow-start-default-inputs.txt`: workflow START 默认输入回归通过。
- `e2e-chatflow-parameters.txt`: chatflow 输入/输出控件回归通过。
- `e2e-chatflow-node-test-after-message-fix.txt`: chatflow 单节点试运行使用 MESSAGE 节点确定性通过，未继续执行下游 END。

## Browser UAT

- URL: `http://127.0.0.1:5173/chatflows/create`
- 操作：打开 END 配置面板，在“回答内容”输入 `{{`，确认 inline picker 显示 `sys.query / sys.conversation_id / sys.user_id / sys.channel / sys.channel_id` 且不显示原始 `{{...}}` 路径；在输出变量值 picker 中展开“开始”，确认同一组系统变量可选。
- 截图：`screenshots/browser-uat-chatflow-end-defaults.png`
- 结束后恢复内置浏览器到 `http://127.0.0.1:5173/workflows/6217/canvas`。
