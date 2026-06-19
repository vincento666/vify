# Slice Reports: 194 Workflow/Chatflow Productionization Phase 1

## 194.1 Runtime V2 Coverage Closure

修改范围：

- `app/modules/workflow/domain/runtime_v2.py`
- `app/modules/workflow/domain/service.py`
- `app/modules/workflow/web/router.py`
- `tests/integration/workflow/test_runtime_v2_api_call_node.py`
- `tests/integration/workflow/test_runtime_v2_tool_call_node.py`
- `tests/integration/workflow/test_runtime_v2_llm_callable_tools.py`

红测证据：

- `194.1/red.txt`: runtime v2 未承载 `API_CALL` / `TOOL_CALL` / LLM callable tools 时失败。

实现摘要：

- runtime v2 接入 `API_CALL` 和 `TOOL_CALL` 执行器。
- API/Tool 输出统一补 runtime v2 evidence 默认字段。
- LLM callable tools 在 runtime v2 下接入 MCP tool executor。
- 兼容性检查允许生产安全的 API/Tool 资源配置，并拒绝 direct URL 等 unsafe 配置。

已跑门禁：

- `194.1/unit.txt`
- `194.1/integration.txt`
- `194.1/regression.txt`
- `combined-runtime-v2-production-gate.txt`

剩余风险：

- API/MCP resource readiness 的深度 health/schema 校验仍偏运行期，发布前只覆盖基础合同。

## 194.2 Unified Error Routing

修改范围：

- `app/modules/workflow/domain/runtime_v2.py`
- `tests/unit/workflow/test_runtime_v2_core.py`
- `tests/integration/workflow/test_runtime_v2_error_routing.py`

红测证据：

- `194.2/red-runtime-v2-error-routing.txt`: `continue` 被标记为 run failed，`branch` 被 runtime v2 branching compatibility 拒绝。
- `194.2/red.txt`: publish validation 缺少 error outlet 时曾放行。

实现摘要：

- runtime v2 兼容性检查允许 `LLM`、`API_CALL`、`TOOL_CALL`、`CODE`、`EXECUTE_WORKFLOW`、`AGENT_CALL` 的显式 `errorBehavior=branch` 多出口图。
- runtime v2 执行期统一捕获六类可失败节点的异常，支持：
  - `fail`: 保持节点/run 失败。
  - `continue`: 输出 `success=false`、`error`、`errorBehavior`、`evidence` 并走默认出口。
  - `branch`: 输出同样错误证据并设置 `route=error`。
- 增加 `workflow_node_error_handled` durable event，保留 `workflow_node_completed` 和 node status `COMPLETED`。

已跑门禁：

- `194.2/unit-integration.txt`
- `194.2/integration-runtime-v2-error-routing.txt`
- `combined-runtime-v2-production-gate.txt`

剩余风险：

- 集成测试真实覆盖 CODE 和 AGENT_CALL；六类节点的输出标准化由核心单测覆盖，API/Tool 的运行时错误细节仍依赖各自 executor/evidence 测试。

## 194.3 API/Tool Production Governance

修改范围：

- `frontend/src/views/workflow/WorkflowCreate.vue`
- `frontend/src/views/workflow/workflowValidation.ts`
- `frontend/src/views/workflow/workflowValidation.test.ts`
- `frontend/src/views/workflow/chatflowDebugTimeline.ts`
- `frontend/src/views/workflow/chatflowDebugTimeline.test.ts`
- `frontend/src/views/workflow/chatflowRunDebug.ts`
- `frontend/src/views/workflow/chatflowRunDebug.test.ts`

红测证据：

- `194.3/red.txt`: API/Tool governance 必填、failure evidence 展示、变量快照投影缺失。

实现摘要：

- API_CALL frontend validation 要求 auth mode、timeout、retry、errorBehavior、output schema 和敏感 header redaction。
- TOOL_CALL frontend validation 要求 timeout、retry、errorBehavior 和 output schema。
- WorkflowCreate 暴露 API/Tool 调用治理字段并写入 node config。
- Chatflow timeline 展示 runtime v2 failure/evidence，并脱敏 Authorization/token 等敏感值。
- Chatflow runtime v2 session projection 保留 `variables`。

已跑门禁：

- `194.3/unit.txt`
- `194.5/rem.txt`
- `194.5/unit.txt`
- `194.6/frontend-unit-full.txt`

剩余风险：

- 尚未跑浏览器 UAT；既有 E2E fixtures 若创建缺少治理字段的 API/Tool 节点，可能需要同步补 fixture。

## 194.4 Snapshot and Version Binding

修改范围：

- `app/modules/workflow/domain/runtime_v2.py`
- `app/modules/workflow/domain/service.py`
- `tests/integration/workflow/test_runtime_v2_execute_workflow_published_snapshot.py`
- `tests/integration/workflow/test_workflow_publish_versions.py`

红测证据：

- `194.4/red.txt`: nested `EXECUTE_WORKFLOW` 在子 workflow 发布后编辑草稿时跑出草稿内容，证明受 draft 漂移影响。

实现摘要：

- runtime v2 nested `EXECUTE_WORKFLOW` 通过 published snapshot repository 执行。
- nested 输出补 `nestedVersionId` / `nestedVersion`。
- published run snapshot repository 支持目标 workflow 读取 active published snapshot。

已跑门禁：

- `194.4/integration.txt`
- `combined-runtime-v2-production-gate.txt`

剩余风险：

- 后续若支持指定 nested versionId，需要扩展 config/schema；当前覆盖 active published child version。

## 194.5 Validation and Variable Contract

修改范围：

- `app/modules/workflow/domain/graph_validation.py`
- `app/modules/workflow/domain/service.py`
- `app/modules/workflow/domain/runtime_v2.py`
- `frontend/src/views/workflow/workflowValidation.ts`
- `frontend/src/views/workflow/workflowValidation.test.ts`
- `tests/unit/workflow/test_publish_validation.py`

红测证据：

- `194.5/red.txt`: invalid variable reference、写 `sys.*`、CODE 缺 code、非法 output type、非法 modelConfigId、未发布子 workflow、无效 model config 曾被放行。

实现摘要：

- 新增 graph validation hooks：错误分支 endpoint、变量引用、系统变量只读、基础必填/type contract。
- publish 前合并结构校验和 readiness 校验：子 workflow active published version、LLM model enabled/ready、Agent target 基础 readiness。
- runtime v2 compatibility 接入 contract/reference validation，运行前拒绝 invalid graph。
- 前端 API/Tool/变量相关验证与 debug dock 展示对齐。

已跑门禁：

- `194.5/unit.txt`
- `194.5/rem.txt`
- `combined-runtime-validation-gate.txt`
- `combined-runtime-v2-production-gate.txt`

剩余风险：

- API/MCP resource publish-time health/schema readiness 尚未完整前置，仍主要依赖 runtime resource registry 和执行 evidence。
