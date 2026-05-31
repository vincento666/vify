# Spec 012: Chatflow Visual Canvas

## Goal

Add Chatflow as a separate product resource entry with its own list and create button, while reusing the Workflow visual canvas, node registry, graph persistence, validation, and executor foundation. Chatflow adds conversation-aware variables and test-run behavior needed for AI customer-service scenarios.

## Product Boundary

- Chatflow is not a filter label inside Workflow List; it has a sibling Chatflow List under the workflow module tabs.
- Chatflow shares the FlowGraph language with Workflow.
- Chatflow baseline includes variable scopes and conversation test profile only.
- Dify-style multi-task dynamic switching, Task Stack, and cross-flow resume are explicitly out of scope and reserved for a later spec.

## User Value

Chatflow authors can build conversational service flows that read user input, conversation identity, channel, user identity, dialogue round, files, and conversation/user/channel variables without duplicating workflow canvas behavior.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 012.1 Chatflow resource entry | Workflow module exposes Chatflow tab with its own list, create button, detail route, and empty/default states | RED: chatflow route/list test fails; Unit: route/type helpers; Integration: resource type persists; E2E: tab navigation; UAT: Chatflow list visible |
| 012.2 Shared graph model | Chatflow graph persists through shared nodes/edges with flow type separation and default START/END chat variables | RED: create detail test fails; Unit: flow type schema; Integration: list separation; E2E: create chatflow; UAT: reopen graph |
| 012.3 Variable panel | Chatflow canvas left panel supports System, Global, Conversation, User, Channel, and External Input variables | RED: variable panel test fails; Unit: variable catalog; Integration: config round-trip; E2E: add variable reference; UAT: variables visible |
| 012.4 Conversation test run | Chatflow test panel accepts message and conversation profile, injects system variables, runs shared executor, and writes visible message-style output | RED: chatflow run test fails; Unit: system variable mapping; Integration: run input contract; E2E: message test output; UAT: conversation result visible |
| 012.5 Chatflow publish/open shell | Chatflow publish/open shells show channel/API fields and block publish until validation and test pass | RED: chatflow publish guard fails; Unit: guard; Integration: status compatible; E2E: guard path; UAT: channel fields visible |

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

## Stop Conditions

- No Task Stack.
- No automatic intent switching across independent Chatflows.
- No cross-flow interrupt/resume.
- No real channel adapters.
- No durable variable store beyond mock/config persistence unless a later spec adds it.

## Evidence

- HiAgent research supplied in conversation: Chatflow and Workflow are separate product entries, share FlowGraph and executor, differ by conversational runtime profile.
- Coze login-gate screenshot: `artifacts/research/coze-workflow/coze-edge-initial.png`.
- Slice evidence: `artifacts/slices/012-chatflow-visual-canvas/{slice-id}/`.
