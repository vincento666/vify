# Plan — Spec 218

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 218.1 把基础底座（DB engine / pool config）做稳，让后续 slice 有可靠的 SQL 写入路径。
- 218.2 / 218.3 / 218.4 / 218.5 沿 "claim → heartbeat → retry → DLQ" 推进。
- 218.6 把幂等 + proposed action 三层（run / job / node）拉齐。
- 218.7 单独验证独立 worker 进程 + 请求线程 offload。
- 218.8 出口回归。

## 关键风险

- 风险 1：job claim 原子化在 MySQL 上需要 `SELECT ... FOR UPDATE SKIP LOCKED`，受 MySQL 版本约束。
  - 缓解：218.2 用 `SELECT ... FOR UPDATE SKIP LOCKED`（MySQL 8.x 支持，已是项目基线）；contract 测试压并发 20 worker。
- 风险 2：heartbeat 频率 / lease 时长选择不当会让"假死"误判率高。
  - 缓解：218.3 把 heartbeat / lease 写到 schema-driven 配置；默认值经合约测试覆盖。
- 风险 3：retry 与重试时 side-effect 节点的幂等保护交互复杂。
  - 缓解：218.4 + 218.6 联合设计；幂等键写在 job + node_run 双层。
- 风险 4：DLQ 重试可能再次进入失败循环。
  - 缓解：DLQ retry 支持"次数上限 + 强制 reset attempt"；contract 覆盖。
- 风险 5：独立 worker 进程引入新的进程间状态。
  - 缓解：218.7 沿用 anyio CapacityLimiter；进程间通过 DB 状态 + Redis 流（spec 219 加）协调；本 spec 不引入 Redis stream。

## 与其他 spec 的相互影响

- 与 spec 217：side-effect 节点幂等键 schema 必须与本 spec 的 job 幂等键设计兼容。
- 与 spec 219：DLQ / 重试 / 限流共用一套配置语义；219 在本 spec 之上加 cancel / rate limit / backpressure。
- 与 spec 220：DLQ / job / worker / heartbeat 数据是观测面板的事实源。
- 与 spec 221：本 spec 完成后才允许做生产容量与故障演练。

## 工程任务序列

1. 218.1 → 218.2 → 218.3 → 218.4 → 218.5 → 218.6 → 218.7 → 218.8。
2. 每个 slice 完成后跑 spec 212.5 入口门禁子集做轻量回归。

## 出口条件（Definition of Done for the whole spec）

- DB engine / session factory 全局复用并可配置；连接池参数走 schema-driven。
- Job claim 原子化；heartbeat / lease renew / worker crash 接管在 contract / integration 上有证据。
- Retry / DLQ / 幂等 / proposed action 三层全部覆盖。
- 请求线程不再执行长任务；独立 worker 进程入口可启动并消费 job。
- spec 212-217 入口门禁回归全绿。
