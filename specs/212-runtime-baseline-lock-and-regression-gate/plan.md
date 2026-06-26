# Plan — Spec 212

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- slice 212.0 / 212.1 / 212.2 是修复 baseline 已发现的 LOGIC-RED 与配置缺口。
- slice 212.3 把执行约定写进 `acceptance-gates.md`，让 spec 213+ 复用同一组检查命令。
- slice 212.4 在 pgvector 起来后扩展验收覆盖面，但不引入新业务能力。
- slice 212.5 是"全绿入口闸"：所有 gates 一次性重跑，归档为 spec 213+ 的进入门禁。

## 关键风险

- 风险 1：`pyproject.toml` pytest pythonpath 配置改动可能影响 uv 缓存与 CI；
  - 缓解：变更前后分别跑 contract / unit 套件，确保零回归；保留 `PYTHONPATH=.` 兼容指令在 acceptance-gates 文档中作为环境回退。
- 风险 2：`customer-assistant-chatflow-runtime-gateway-uat` 中 operator-task-ledger 时序问题可能是后端推送顺序导致的事件丢帧；
  - 缓解：先用 RED 录像/截图定位丢帧节点，再在 frontend e2e wait 条件或后端 publisher 双向定位根因，禁止只在 UAT 加 sleep。
- 风险 3：pgvector 起来后部分依赖 RAG 的脚本可能出现新红测；
  - 缓解：slice 212.4 单独归档 pgvector-dependent UAT 结果，新增红测拉一个 micro slice（212.4.x）单点解决，不污染 212.5 ALL GREEN 入口。
- 风险 4：Chrome-MCP harness 增补可能与现有自动化脚本签名不兼容；
  - 缓解：212.3 只增补"调用约定"和"判定口径"，不重写脚本本身；具体迁移留到 spec 220 观测面板 UAT 阶段。

## 与其他 spec 的相互影响

- 与 spec 213：212.5 的全绿门禁是 213 启动条件；213 引入 async default 后，需要 212 定义的"基础回归门禁"作为 release safety net。
- 与 spec 220：212.3 增补的 Chrome-MCP 约定会被 220 观测面板的 UAT 直接复用。
- 与 spec 221：212.5 归档的 baseline.md 是 221 容量报告的对照基线，禁止在 212 完成后回改。

## 工程任务序列

1. 完成 212.0 配置修复，让 contract gate 不再依赖 `PYTHONPATH=.` 前缀。
2. 完成 212.1 / 212.2 两个 LOGIC-RED 修复，所属测试转 GREEN 并归档证据。
3. 完成 212.3 文档增补，提交后让 spec 213+ 可引用新口径。
4. 完成 212.4 pgvector UAT 子集补跑。
5. 完成 212.5 整套基线重跑，所有 gates ALL GREEN，归档证据后冻结 baseline.md。

## 出口条件（Definition of Done for the whole spec）

- backend unit / integration / contract 三套套件全绿，且 contract 套件不再需要 `PYTHONPATH=.` 前缀。
- frontend unit + remScaleClosure 全绿。
- Chatflow 核心 UAT、SOP UAT、Workflow 核心 UAT 子集全部 PASS（含 212.1 / 212.2 修复后的脚本）。
- pgvector-dependent UAT 子集 PASS 或归档为单独 ENV-BLOCKED 项并升级。
- `docs/testing/acceptance-gates.md` 包含 Chrome-MCP harness 调用约定。
- `artifacts/slices/212-runtime-baseline-lock-and-regression-gate/212.5/` 下归档完整 gate 证据，并在 baseline.md 标记 "ALL GREEN @ SHA <sha>"，作为 spec 213+ 入口签收点。
