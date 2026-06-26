# Plan — Spec 217

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 217.1 先把矩阵列清楚，让后续 slice 有覆盖度对照。
- 217.2 / 217.3 把 LLM / Knowledge / Agent / API / Tool / Execute Workflow 6 类节点的并发场景分两批落 RED → GREEN。
- 217.4 单独处理 side-effect 节点的幂等键 / proposed action 保护。
- 217.5 把非法配置错误从运行时挪到 compatibility check。
- 217.6 收敛 Chatflow / Workflow 能力一致性差异。
- 217.7 出口回归。

## 关键风险

- 风险 1：某节点 executor 在并发下共享单例 client 导致 race。
  - 缓解：217.2 / 217.3 给每个并发 case 加 contract 测试断言 input / output 不串扰；client 使用上下文绑定。
- 风险 2：幂等键设计不当导致 retry 时不写真实结果。
  - 缓解：217.4 在合约层定义"幂等键 = run_id + node_run_id + payload hash"；side-effect 节点必须显式声明 idempotency key 字段。
- 风险 3：compatibility check 暴露的 error 不可读 / 不本地化。
  - 缓解：217.5 给所有非法配置错误指定 `ErrorCode` 与人类可读 message；前端单测验证文案。
- 风险 4：Chatflow / Workflow 同类节点能力差异可能源于产品语义；强行对齐会破坏功能。
  - 缓解：217.6 给"明确产品语义差异"的节点保留差异并写在文档里。

## 与其他 spec 的相互影响

- 与 spec 215：所有并发场景依赖 215 的 scheduler。
- 与 spec 218：side-effect 节点幂等键设计是 218 job retry 安全的基础。
- 与 spec 220：节点兼容矩阵是观测面板节点详情页的元数据来源。

## 工程任务序列

1. 217.1 节点矩阵 + 自动化扫描；
2. 217.2 LLM / Knowledge / Agent 并发；
3. 217.3 API / Tool / Execute Workflow 并发；
4. 217.4 Side-effect 节点幂等；
5. 217.5 compatibility check；
6. 217.6 Chatflow / Workflow 能力一致性；
7. 217.7 出口回归。

## 出口条件（Definition of Done for the whole spec）

- `docs/runtime/node-compatibility-matrix.md` 落地，覆盖所有一等节点。
- 6 类核心节点在 DAG 并发下通过 contract + integration + e2e 测试。
- Side-effect 节点全部具备幂等键 / 执行记录 / proposed action 保护。
- 非法配置 compatibility check 报错；运行时 unsupported error 在搜索中 0 命中。
- Chatflow / Workflow 同类节点能力一致或差异有文档证据。
- spec 212-216 入口门禁回归全绿。
