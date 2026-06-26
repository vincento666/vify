# Plan — Spec 215

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 先在数据层做出 node state graph + frontier 计算的无副作用模块（215.1），再切换执行入口（215.2）。
- 并发执行（215.3）通过 anyio task group 实现，遵守 CLAUDE.md 的并发上限规范，禁止 unbounded fan-out。
- 状态传播 / 失败策略 / 事件 sequence 是三条互相影响的横切线，分三个 slice 串行实现，每条都用 contract 套件钉死。
- 215.7 出口必须重跑 212+213+214 全部入口门禁，保证 scheduler 升级未把任何前置 spec 的行为打回。

## 关键风险

- 风险 1：并发 fan-out 把同一 run 的变量作用域写串扰。
  - 缓解：215.3 的 contract 套件断言每个 node run 写自己的 scope；scope 写入路径加 `run_id + node_run_id` 复合键校验。
- 风险 2：事件 sequence 在并发下出现 race。
  - 缓解：215.6 用单 writer goroutine（async lock）保护 sequence；contract 测试压并发 10 节点同时完成，断言 sequence 严格单调递增。
- 风险 3：失败策略矩阵会触碰熔断、retry、deadline 的相互依赖。
  - 缓解：本 spec 只实现 scheduler 层的 4 类策略；timeout / 熔断 / DLQ 留给 spec 218+219。
- 风险 4：run 完成判定从"最后一个节点"改为"active path 完成"可能让某些 UAT 在 final event 上断言失败。
  - 缓解：215.4 用合约测试覆盖 active path 完成各种组合，UAT 端先 RED 再修。
- 风险 5：scheduler 切换可能影响 Chatflow waiting input、resume 行为。
  - 缓解：215.2 与 215.4 共同覆盖 waiting 状态语义；spec 216 会进一步在 Chatflow / SOP 兼容侧补 UAT。

## 与其他 spec 的相互影响

- 与 spec 214：本 spec 是 214 语义的执行实现；不得新增 214 未声明的语义。
- 与 spec 216：本 spec 完成后才允许 spec 216 全面 UAT Chatflow / SOP 多路径兼容。
- 与 spec 218：scheduler 的并发执行 + 失败策略与 job lease / retry / DLQ 设计耦合；218 阶段会在本 spec 基础上加 job 层。
- 与 spec 219：事件 sequence、取消、限流要求基于本 spec 实现的 frontier 调度。

## 工程任务序列

1. 完成 215.1 数据结构。
2. 完成 215.2 单顺序链路 GREEN，确保零回归。
3. 完成 215.3 并发执行 + 作用域隔离。
4. 完成 215.4 状态传播 + 完成判定 + side-effect terminal。
5. 完成 215.5 失败策略矩阵。
6. 完成 215.6 事件 sequence 并发一致性。
7. 完成 215.7 出口回归。

## 出口条件（Definition of Done for the whole spec）

- runtime engine 使用 frontier-based scheduler；旧 single-path while-loop 代码路径删除（或仅在 legacy compat 中保留并标注 deprecated）。
- 并发 fan-out 在合约 + 集成 + UAT 上有证据。
- 失败策略矩阵 4 类全部覆盖，且配置走 schema-driven。
- 事件 sequence 并发下单调递增。
- spec 212 + 213 + 214 全套入口门禁回归全绿。
