# Plan — Spec 214

## 实施策略

按 RED → GREEN → REFACTOR 串行推进 slice 列表。每个 slice 必须先写红测证据再写最小实现。

- 214.1 先定义语义文档与 schema，使 RED 测试有可对照的"应有"行为。
- 214.2 把语义落到画布校验（前后端两边），形成"编辑期"防线。
- 214.3 把语义投影到 runtime 数据模型，但保留单路径执行行为（不接 scheduler），让 spec 215 可平滑切换。
- 214.4 锁定 Chatflow / Workflow 最终输出规则。
- 214.5 回归与文档收尾。

## 关键风险

- 风险 1：语义文档与代码不一致，spec 215 实现 scheduler 时出现"语义二义性"。
  - 缓解：214.1 用 schema + 合约测试把每条语义钉死；214.5 出口要求文档与 schema 一致校验通过。
- 风险 2：画布校验新增报错可能让既有合法图（边角案例）误报。
  - 缓解：214.2 在合法案例集合上做白名单测试；先 RED 收集所有非法 case 再实现校验。
- 风险 3：runtime 数据模型新增 selected / skipped 状态可能影响 ORM migration。
  - 缓解：214.3 提供 Alembic migration + downgrade；只新增字段，不删旧字段，保持 spec 213 接口稳定。
- 风险 4：Chatflow 最终回复规则与现有 End / answer / message 节点行为有 overlap。
  - 缓解：214.4 用合约测试覆盖 "End 优先 / answer mapping 次之 / priority / side-effect-only" 四种情形。

## 与其他 spec 的相互影响

- 与 spec 215：本 spec 是 215 的语义前置；215 不得新增任何与 214 不一致的语义。
- 与 spec 216：Chatflow / SOP 兼容验收依赖 214 的最终回复规则。
- 与 spec 217：节点兼容矩阵中 "支持 fan-out / branch / side-effect terminal" 标记由 214 定义。

## 工程任务序列

1. 完成 214.1 文档 + Pydantic schema + 合约测试。
2. 完成 214.2 画布校验前后端联动。
3. 完成 214.3 runtime 数据模型新增字段 + Alembic migration（保持执行路径不变）。
4. 完成 214.4 Chatflow / Workflow 最终输出规则合约。
5. 完成 214.5 出口回归。

## 出口条件（Definition of Done for the whole spec）

- `docs/runtime/dag-semantics.md` 落地，覆盖 edge / port / branch / skipped / terminal / final-output。
- 画布校验在前后端两侧识别合法 fan-out / 多分支 / side-effect terminal / 隐式 join / 非法孤岛。
- runtime 数据模型新增 selected / skipped 状态字段并通过 migration。
- Chatflow / Workflow 最终输出规则有合约测试覆盖。
- spec 212 + 213 入口门禁回归全绿。
