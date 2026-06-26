# Plan — Spec 221

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 221.1 → 221.2 在本机做 20-50 / 100-200 并发 baseline。
- 221.3 → 221.8 是六个类生产演练（多 worker / DAG fan-out / resume / worker crash / DB-Redis 故障 / 慢调用）。
- 221.9 汇总容量报告。
- 221.10 出口回归。

## 关键风险

- 风险 1：本机压测易把硬件瓶颈误判为系统瓶颈。
  - 缓解：221.1 / 221.2 同时记录 CPU / 内存 / 文件描述符 / DB 连接数；判定阈值写在 schema-driven 阈值表里，超过阈值才标 RED。
- 风险 2：类生产 chaos 演练对开发环境影响大（杀进程 / 断 DB / 断 Redis）。
  - 缓解：221 阶段在专门 docker compose 环境执行；脚本可重入；演练前后留 snapshot。
- 风险 3：容量报告字段口径若与 spec 220 观测面板字段不一致，会让"面板看到的"与"压测报告写的"对不上。
  - 缓解：221.9 报告字段直接复用 spec 220 暴露的字段名；不允许私自起新名。
- 风险 4：慢调用演练可能错误标记真实 provider 异常为系统 bug。
  - 缓解：221.8 用受控的 mock provider 实现慢响应；记录是否触发 deadline / 熔断 / 背压。

## 与其他 spec 的相互影响

- 与 spec 215：本 spec 用 frontier scheduler 跑 DAG fan-out 压测。
- 与 spec 218：本 spec 用 job lease / DLQ / retry 跑多 worker / worker crash 演练。
- 与 spec 219：本 spec 用 cancel / 限流 / 背压 / 压缩跑慢调用与高频事件演练。
- 与 spec 220：本 spec 用观测面板字段口径输出容量报告。

## 工程任务序列

1. 221.1 → 221.2 → 221.3 → 221.4 → 221.5 → 221.6 → 221.7 → 221.8 → 221.9 → 221.10。

## 出口条件（Definition of Done for the whole spec）

- 本机 20-50 / 100-200 并发功能正确性 + 烟测均通过。
- 多 worker / DAG fan-out / interrupt-resume / worker crash / DB-Redis / 慢调用 6 项演练全部通过。
- 输出 `docs/runtime/capacity-report.md`，含 p50 / p95 / p99 / queue latency / node latency / event delay / 错误率 / 资源占用。
- spec 212-220 入口门禁回归全绿。
