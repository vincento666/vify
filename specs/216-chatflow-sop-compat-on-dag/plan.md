# Plan — Spec 216

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 216.1 / 216.2 关注 Chatflow 单元：中断恢复 + 最终回复规则，先把单图行为补齐。
- 216.3 / 216.4 关注 SOP Router 与 child Chatflow 边界，是本 spec 的合规重点。
- 216.5 关注客服 worker 状态机消费。
- 216.6 出口回归 212+213+214+215。

## 关键风险

- 风险 1：DAG 下 waiting 节点集合表达若与 Chatflow 旧"单 waiting"假设不一致，会让前端等待 UI 表现异常。
  - 缓解：216.1 在 contract 层显式定义 `waitingNodes`（数组），前端单测覆盖单/多 waiting 的渲染。
- 风险 2：resume 在并发 fan-out 下可能重跑已完成 side-effect 节点。
  - 缓解：216.1 的 contract 测试钉死 "resume 只恢复 waiting，不重跑 completed"；checkpoint 中带每个 node run 的完成证据。
- 风险 3：SOP Router 历史代码可能在多处直接读 / 写 `current_step` 等字段；删字段会引发大规模回归。
  - 缓解：216.3 先在 service 层提供"聚合视图"（read-through），再渐进删除写入路径；旧字段先 deprecated，最后整批删除。
- 风险 4：12 条 SOP UAT 矩阵中部分场景 (resume offer、不可中断步骤拒绝切换) 在当前画布上没有对应 fixture。
  - 缓解：216.4 在 `frontend/e2e/fixtures/` 或 `tests/fixtures/` 增补 fixture；不允许把 case 标 skip。

## 与其他 spec 的相互影响

- 与 spec 215：本 spec 必须不引入新的 scheduler 能力。
- 与 spec 217：waiting / cancelled 状态可能涉及节点 executor 行为；217 中按节点单点验收。
- 与 spec 218：resume / waiting / cancelled 状态在 job 层有对应表现；本 spec 不引入 job lease。
- 与 spec 220：本 spec 锁定的 ledger 字段集是 220 观测面板列表字段的源头。

## 工程任务序列

1. 216.1 Chatflow 中断 / resume；
2. 216.2 Chatflow 最终回复规则；
3. 216.3 SOP Router ledger 收敛 + 聚合视图；
4. 216.4 SOP UAT 矩阵 12 条；
5. 216.5 客服 worker 状态机；
6. 216.6 出口回归。

## 出口条件（Definition of Done for the whole spec）

- Chatflow 中断 / resume 在 DAG 下行为合约通过；resume 不重跑 completed side-effect 节点。
- Chatflow 最终回复规则有合约测试和 UAT 证据。
- SOP Router ledger 字段集白名单生效；`current_step / pending_prompt / collected / scoped_variables / checkpoint / node events / run status` 通过聚合视图返回。
- SOP UAT 12 条矩阵在 API / 事件流 / 任务面板 / 刷新恢复四个维度全部通过。
- 客服 worker 5 状态消费通过 e2e。
- spec 212-215 入口门禁回归全绿。
