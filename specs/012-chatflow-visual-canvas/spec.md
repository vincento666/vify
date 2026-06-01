# Spec 012: Chatflow Visual Canvas

## Goal

Add Chatflow as a separate product resource entry with its own list and create button, while reusing the Workflow visual canvas, node registry, graph persistence, validation, and executor foundation. Chatflow adds conversation-aware variables and test-run behavior needed for AI customer-service scenarios.

## Product Boundary

- Chatflow is not a filter label inside Workflow List; it has a sibling Chatflow List under the workflow module tabs.
- Chatflow shares the FlowGraph language and persistence tables with Workflow, separated internally by `flow_type=CHATFLOW`.
- Chatflow baseline includes variable scopes and conversation test profile only.
- Dify-style multi-task dynamic switching, Task Stack, and cross-flow resume are explicitly out of scope and reserved for a later spec.
- Chatflow canvas reuses the Coze-like node card, port, edge, right-panel configuration, bottom toolbar, add-node popover, and bottom debug model from Workflow canvas, adding only Chatflow-specific variable and conversation surfaces.
- Chatflow node configuration uses the same minimal runtime-backed field boundary as Workflow canvas; Chatflow-specific UI appears in variable and conversation test panels, not in duplicated node forms.
- Chatflow variable selector extends the Workflow selector with system/scoped variables such as `sys.query`, `sys.conversation_id`, `sys.user_id`, and `sys.channel`. Node-output selection still obeys the connected-upstream-only rule.

## User Value

Chatflow authors can build conversational service flows that read user input, conversation identity, channel, user identity, dialogue round, files, and conversation/user/channel variables without duplicating workflow canvas behavior.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 012.1 Chatflow resource entry | Workflow module exposes Chatflow tab with its own list, create button, detail route, and empty/default states | RED: chatflow route/list test fails; Unit: route/type helpers; Integration: resource type persists; E2E: tab navigation; UAT: Chatflow list visible |
| 012.2 Shared graph model | Chatflow graph persists through shared nodes/edges with `flow_type=CHATFLOW` separation and default START/END chat variables | RED: create detail test fails; Unit: flow type schema; Integration: list separation; E2E: create chatflow; UAT: reopen graph |
| 012.3 Variable panel and picker | Chatflow canvas left panel supports System, Global, Conversation, User, Channel, and External Input variables; node fields can insert these references through the shared picker | RED: variable panel test fails; Unit: variable catalog; Integration: config round-trip; E2E: add variable reference; UAT: variables visible |
| 012.4 Chatflow input/output controls | Chatflow nodes use the shared input/output parameter editors and add system/scoped variables to reference mode | RED: chatflow parameter editor test fails; Unit: system/scoped variable catalog; Integration: config round-trip; E2E: select `sys.query`; UAT: control works |
| 012.5 Conversation test run | Chatflow test panel accepts message and conversation profile, injects system variables, runs shared executor, and writes visible message-style output | RED: chatflow run test fails; Unit: system variable mapping; Integration: run input contract; E2E: message test output; UAT: conversation result visible |
| 012.6 Chatflow publish/open shell | Chatflow publish/open shells show channel/API fields and block publish until validation and test pass | RED: chatflow publish guard fails; Unit: guard; Integration: status compatible; E2E: guard path; UAT: channel fields visible |
| 012.7 Coze debug/run polish | Chatflow run/test UI matches the current Coze shared debug surface: conversation-shaped input/profile controls plus bottom `调试` result detail | RED: debug/run visual test fails; Unit: debug form state; E2E: open run surface, edit input, close result detail; UAT: run surface matches reference |
| 012.8 Chatflow resource context | Chatflow LLM resource context combines supported Knowledge Resource retrieval with system variables and optional chat history while guarding unsupported tools/subflows | RED: chatflow resource context test fails; Unit: runtime profile context; Integration: run/guard; E2E: support state; UAT: status clear |
| 012.9 Chatflow single-node test profile | Chatflow selected-node tests reuse Workflow node-test UI while injecting Chatflow system variables, scoped variables, and optional bounded history | RED: chatflow node test fails; Unit: profile fixture builder; Integration: selected node run/profile; E2E: run selected Chatflow LLM node; UAT: node-only conversational input visible |

## Default System Variables

- `sys.query`: current user message.
- `sys.conversation_id`: current conversation identity.
- `sys.conversation_name`: current conversation name.
- `sys.user_id`: current user identity.
- `sys.channel`: invocation channel such as `web`, `api`, `feishu`, `dingtalk`.
- `sys.now`: current system time.
- `sys.message_id`: current message identity.
- `sys.round`: current dialogue round.
- `sys.files`: uploaded files for the current turn.

## Variable Scopes

- System: platform-provided, read-only.
- Global: shared at product/resource level.
- Conversation: tied to one conversation; default short-lived in future storage.
- User: tied to one user; long-lived.
- Channel: tied to channel configuration.
- External Input: supplied by one API or SDK call.

## Basic Control Reuse

Chatflow reuses Workflow basic parameter controls from 011:

- Shared Variable Reference Picker.
- Shared Input Parameter Editor.
- Shared Output Parameter Editor.
- Shared Coze-style panel section layout.

Chatflow extends picker scope with system/scoped variables, but connected node-output selection still follows the upstream-only rule.

For Chatflow LLM nodes, the output area follows the Coze reference: output format selector with `文本`, `Markdown`, and `JSON`, output variable rows with variable name and variable type selector, expand/detail action, delete action, and add output variable action. Declared outputs automatically enter the downstream reference pool; there is no separate "can be referenced downstream" switch.

For Chatflow LLM nodes, the input area adds a `会话历史` toggle next to the input section title. When enabled, the Chatflow runtime profile passes the current conversation history into the LLM prompt context. Workflow LLM nodes do not show this toggle.

Chatflow LLM input variable chips can reference system/start variables such as `USER_INPUT`, `CONVERSATION_NAME`, and future scoped system variables through the shared picker. The picker still must reject disconnected downstream node outputs.

Chatflow reuses the Workflow LLM Unified Resource boundary:

- Knowledge Base resources may be retrieved and inserted into the LLM context together with Chatflow system variables and optional conversation history.
- MCP Tool resources are not current-stage Chatflow LLM behavior unless the Chatflow runtime profile wires tool-call schema, execution, second LLM round, and message/run evidence.
- Subworkflow resources are not current-stage Chatflow LLM behavior unless nested run, interrupt/resume, recursion, and output mapping rules are specified.
- Coze Chatflow/Agent skill vocabulary includes Knowledge, Plugin, Workflow, and Imageflow. Hify should show only supported/currently planned resource types; Imageflow remains out of MVP.

Advanced Chatflow-only fields wait until the shared basic controls are working across current nodes.

Chatflow selected-node testing reuses the Workflow single-node test action, but the fixture builder must include Chatflow system variables such as `sys.query`, `sys.conversation_id`, `sys.user_id`, and `sys.channel`. If the selected LLM node has `会话历史` enabled, the node test fixture exposes bounded editable/mock history instead of reading arbitrary production history.

## Chatflow Debug And Run UX

The authenticated live Coze reference on 2026-06-01 shows the `/work_flow` route rendering shared Workflow/Chatflow canvas chrome. Start inputs include `USER_INPUT`, `CONVERSATION_NAME`, and an overflow `...` chip. The observed run/debug result surface is a bottom dock titled `调试`, with a run tree, `详情` flamegraph/detail area, close action, and sticky `保存并开始对话调试`.

The Chatflow test-run surface must be conversation-shaped rather than generic JSON-shaped:

- Header or entry action: `试运行`, optional `查看日志`, close action.
- Body/input profile: message input and system/scoped variables instead of raw code block output.
- Optional available test dataset selector.
- Linked content section with required agent/app selector shell.
- Test input section with `JSON模式` toggle, `AI 补全` action, typed input rows, and inline required markers.
- Save-current-input checkbox.
- Sticky primary action: `保存并开始对话调试`.
- Bottom `调试` panel remains available for run tree/detail, validation errors, empty states, and close action.
- If Hify uses a right-docked input drawer for initial fixture editing, it must coexist with the shared bottom debug panel and must not obscure the sticky primary action or selected-node right config panel.

## Stop Conditions

- No Task Stack.
- No automatic intent switching across independent Chatflows.
- No cross-flow interrupt/resume.
- No real channel adapters.
- No durable variable store beyond mock/config persistence unless a later spec adds it.

## Evidence

- HiAgent research supplied in conversation: Chatflow and Workflow are separate product entries, share FlowGraph and executor, differ by conversational runtime profile.
- Coze shared canvas and debug audit: `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`.
- Coze live bottom debug screenshot: `artifacts/research/coze-workflow/screenshots/coze-live-bottom-debug-after-trial-click-20260601.png`.
- Coze visual notes: `artifacts/research/coze-workflow/notes.md`.
- Slice evidence: `artifacts/slices/012-chatflow-visual-canvas/{slice-id}/`.
