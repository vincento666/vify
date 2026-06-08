## Research Notes

- HiAgent 2.x screenshot reference: left chatflow settings uses `开场白`, `开场白问题`, and a `记忆` area with `会话变量` plus `用户变量`; voice and safety sections are ignored for this slice.
- Coze Studio public/open-source references show Chatflow is conversation-bound through special start inputs such as `USER_INPUT` and `CONVERSATION_NAME`, and custom variables are passed as runtime/custom variable maps rather than a default full left-panel dump.
- Coze Studio also treats workflow, plugins, databases, knowledge bases, and variables as resources, which supports keeping left settings as a compact entry/summary and using contextual pickers inside node fields.
- Huawei AgentArts variable docs describe memory/global variable configuration as a managed variable surface; the canvas field/picker consumes those variables instead of inventing unconfigured user/app/system groups.

Sources:

- https://github.com/coze-dev/coze-studio/blob/main/README.zh_CN.md
- https://github.com/coze-dev/coze-studio/blob/main/idl/conversation/run.thrift
- https://github.com/coze-dev/coze-studio/blob/main/frontend/packages/arch/resources/studio-i18n-resource/src/locales/zh-CN.json
- https://support.huaweicloud.com/usermanual-agentarts0/agentarts_05_0084.html

## Product Decision

- Rename the left Chatflow variable area to `记忆`.
- Keep variable area light by default: `会话变量 10 · 用户变量 0`, with `会话变量` collapsed.
- Expanded `会话变量` follows HiAgent-like table columns: `变量 key`, `变量显示名`, `操作`.
- Runtime system/session variables are read-only rows with `SYS_*` display keys while retaining real references like `{{sys.query}}`.
- `用户变量` is shown as a persistent-variable explanation with a disabled add icon until a real user-variable configuration backend is specified.

## UAT

- Verified `/chatflows/create` left settings shows `对话设置`, `开场白`, `引导问题`, and compact `记忆`.
- Verified collapsed state does not render variable rows by default.
- Verified expanding `会话变量` renders 10 system/session variable rows with table columns and horizontal-safe row layout.
- Verified clicking `SYS_QUERY` in the left settings panel is read-only and does not open or mutate node config.
- Verified bottom of the left panel shows the `用户变量` explanation and disabled add affordance.

Screenshots:

- `screenshots/hiagent-left-panel-settings-actions-row.png`
- `screenshots/hiagent-left-panel-user-variable-bottom.png`

## Gates

- RED unit: `red-hiagent-unit.txt`
- RED e2e: `red-hiagent-e2e.txt`
- Unit/rem: `rem-unit-hiagent-actions-row.txt`
- Full unit: `full-unit-hiagent.txt`
- E2E settings: `e2e-hiagent-left-panel-settings-actions-row.txt`
- E2E readonly: `e2e-hiagent-left-panel-readonly-wide.txt`
- Build: `build-final.txt`
