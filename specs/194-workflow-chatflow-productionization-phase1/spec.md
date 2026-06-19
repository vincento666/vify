# Spec 194: Workflow/Chatflow Productionization Phase 1

## Goal

将 Hify 当前文字型 Workflow/Chatflow 核心节点生产化，不新增视觉、文件、多媒体、SQL/数据库节点或大规模新节点族。

本 spec 收敛阶段 1 的生产化缺口：runtime v2 默认运行、异常端点、API/Tool 调用治理、变量校验、发布版本快照、调试证据，以及 20 类现有节点字段的真实运行/校验证据。

## Official Reference Baseline

- Coze 低代码工作流、节点、变量、预览调试、日志 Trace、HTTP 请求节点、插件节点、发布/历史。
- Coze Studio 官方 Wiki 的 workflow node type、plugin/model configuration 和 API reference。
- HiAgent/DataAgent 官方 MCP、OpenAPI、REST API、观测接入、审计、版本/发布管理。

Coze 作为节点图和画布调试语义主参考；HiAgent 作为生产治理、MCP、权限、观测、版本审计主参考。

## Scope

In scope:

- 当前 20 类节点：
  `START`, `LLM`, `CONDITION`, `KNOWLEDGE`, `API_CALL`, `TOOL_CALL`,
  `EXECUTE_WORKFLOW`, `AGENT_CALL`, `TRANSFER_TO_HUMAN`, `CODE`,
  `TEXT_PROCESS`, `JSON_PARSE`, `VARIABLE_AGGREGATION`, `VARIABLE_ASSIGN`,
  `INTENT_RECOGNITION`, `MESSAGE`, `QUESTION`, `HUMAN_INPUT`,
  `INFORMATION_COLLECTION`, `END`.
- runtime v2 默认承载 Workflow/Chatflow 运行、状态、事件、节点输入/输出/错误/耗时、变量快照、外部调用 evidence。
- `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`, `EXECUTE_WORKFLOW`, `AGENT_CALL` 的统一异常策略：`fail`, `continue`, `branch`。
- `API_CALL` 生产治理：鉴权、密钥脱敏、query params、headers/body 模板、响应 schema、状态码策略、重试退避、超时、请求/响应预览。
- `TOOL_CALL`/MCP 治理：schema 自动映射、写操作保护、retry、error route、调用 evidence、权限边界。
- 变量系统基础：系统变量只读、用户/会话/流程变量作用域清晰、类型校验、默认值、必填、非法引用提示。
- 发布版本治理：草稿与发布版本分离，运行固定版本，支持回看版本定义，发布前校验覆盖端点、变量、资源、模型。
- 浏览器 UAT 与逐节点验收报告。

Out of scope:

- 视觉、图片、文件、多媒体能力。
- SQL/数据库节点。
- Loop/Batch 等阶段 2 高级节点族。
- 重营销式 UI 文案。
- 为非功能门禁无限新增 spec。

## Hard Constraints

- 不允许通过删除兼容路径、跳过旧 Chatflow/Workflow/SOP 调用方式、降级 runtime v2 来通过测试。
- 不允许让 unsupported graph 静默回旧调试路径作为默认兜底；运行必须明确是 runtime v2 或明确报出不可运行/不可发布原因。
- 所有外部调用 evidence 必须脱敏，不能泄露 secret、Authorization、API key、cookie 或 raw provider credentials。
- 发布版本必须绑定不可变定义快照；指定版本运行不得受草稿编辑影响。
- 每个字段必须至少满足一个：影响保存后的 runtime、影响 debug event/evidence、或触发明确校验结果。
- 每个 slice 必须先保存 RED 证据，再实现，再保存门禁证据。

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 194.1 Runtime v2 coverage closure | `API_CALL`、`TOOL_CALL`、LLM callable tools 进入 runtime v2，20 类节点不再因现有核心节点缺 executor 而回旧路径 | RED: runtime v2 rejects API/Tool; Unit/Integration: API/Tool/LLM-tools run with evidence; Compatibility tests updated |
| 194.2 Unified error routing | 可失败节点支持 `fail`, `continue`, `branch`，错误分支进入统一端点校验 | RED: branch/continue ignored; Unit/Integration: each named node type routes errors correctly; Publish validation rejects missing error branch |
| 194.3 API/Tool production governance | API/Tool 调用具备 auth、脱敏、模板、schema、状态码、retry/backoff、timeout、预览和权限边界 | RED: secrets leak or retry/timeout ignored; Integration/Contract: call evidence sanitized and policy enforced; Frontend unit covers editable governance fields |
| 194.4 Snapshot/version binding | Workflow/Chatflow v2 和 nested `EXECUTE_WORKFLOW` 绑定发布快照，LLM/Agent/Knowledge resolver 不读漂移草稿 | RED: draft edit changes targeted published run; Integration: active/targeted versions stable; Contract: version detail readable |
| 194.5 Validation and variable contract | 运行前/发布前校验覆盖非 END 端点、分支、变量引用、系统变量只读、必填/类型、资源/model readiness | RED: invalid graph publishes/runs; Unit/Frontend unit/Contract: shared errors; rem gate for touched UI |
| 194.6 Evidence and UAT closure | 调试面板、报告和 artifacts 证明 20 类节点字段保存/运行/校验/证据闭环 | Frontend unit + rem, E2E/UAT screenshots, node-by-node report, full backend focused gates |

## Done

- 当前 20 类节点所有表单字段均有保存、运行影响或明确校验/调试证据。
- runtime v2 默认承载运行、事件、节点状态、输入输出、错误、变量快照。
- `LLM`, `API_CALL`, `TOOL_CALL`, `CODE`, `EXECUTE_WORKFLOW`, `AGENT_CALL` 支持统一异常处理端点与校验。
- API/Tool 调用具备鉴权、脱敏、schema 映射、重试、超时、调用 evidence。
- 发布版本绑定不可变定义，发布前校验覆盖端点、变量、资源、模型。
- 单元、集成、契约、前端单测、remScaleClosure、E2E 和浏览器 UAT 证据齐全。
- 输出逐节点验收报告和剩余风险清单，风险收敛到非阻断项。
