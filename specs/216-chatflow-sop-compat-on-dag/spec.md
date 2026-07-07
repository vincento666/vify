# Spec 216: Chatflow / SOP Compatibility on DAG Runtime

> 来源：`docs/chatflow-workflow-production-upgrade.md` §8

## 背景

DAG frontier scheduler 上线后，Chatflow / SOP 这两条对话场景必须保持"逐轮推进"心智不变。spec 216 把 Chatflow 单元（信息收集、问题、人工输入、转人工节点的中断 / resume）、SOP Router 的多级路由、客服 worker 的状态消费、最终回复规则，以及 SOP Router 与 child Chatflow 之间的事实源边界，全部回归并加固。本 spec 不引入新调度能力，而是用 DAG 能力做"语义换底但行为保留"。

## 目标（What）

逐条复用文档 §8 的目标和验收标准：

- 默认 Chatflow 仍表现为清晰的步骤推进。
- 多路径只在明确 fan-out 或 branch 多 target 时发生。
- 信息收集、问题、人工输入、转人工节点仍可中断并 resume。
- 多路径中任一路径 waiting 时，run 能表达等待节点集合。
- resume 只恢复对应等待节点，不重跑已完成 side-effect 节点。
- SOP 多级路由调用 Chatflow 能继续支持意图切换、澄清、信息收集、转人工。
- 客服助手 worker 能正确消费 running / waiting / completed / failed / cancelled 状态。
- SOP Router 的路由账本只保存：conversation id、active child Chatflow session/run、suspended child Chatflow sessions/runs、route decision history、resume offer、intent/task 摘要、必要的展示缓存。
- SOP Router 不单独持有：current_step / pending_prompt / collected / scoped_variables / checkpoint / node events / run status。
- 上述信息必须从 child Chatflow session/run/checkpoint/event 聚合得出。
- 一个客服 conversation 下允许多个 child Chatflow session/run；每个 child Chatflow 独立维护自己的 checkpoint、变量、节点事件和运行状态。
- Chatflow 最终回复规则：End 节点优先；回复节点 / answer mapping 次之；多候选按 priority / output mapping 决定；side-effect-only branch 不参与用户回复；全路径只产生 side effect 时返回结构化执行摘要。

### SOP 完整 UAT 场景矩阵（spec 216 全量交付）

- 新会话首轮命中强意图，启动目标 SOP，并创建对应 child Chatflow session/run。
- 用户补充信息后继续 active SOP，推进到下一等待点或完成。
- 用户在可中断步骤表达新意图，当前 child Chatflow 进入 suspended 映射，新 SOP 创建新的 child Chatflow session/run。
- 新 SOP 完成后，系统给出可恢复旧 SOP 的 resume offer。
- 用户选择恢复旧 SOP，继续原 child Chatflow session/run/checkpoint，而不是新建重复执行状态。
- 用户在不可中断步骤表达新意图，系统拒绝切换并继续当前 SOP。
- 用户表达"继续处理上一个/退回刚才流程"等显式恢复信号，能恢复正确 suspended child Chatflow。
- 用户输入不明确时进入澄清，不误创建新的 child Chatflow run。
- FAQ/RAG 命中时直接回答，不污染 active/suspended child Chatflow 状态。
- Agent fallback 命中时作为问答或建议，不替代 active SOP 的执行状态事实源。
- 转人工时保留 conversation、active/suspended child Chatflow 映射和 runtime refs。
- 多个 child Chatflow 共存时，SOP Router 只展示聚合任务摘要；`current_step / pending_prompt / collected / scoped_variables / checkpoint / node events / run status` 均从对应 child Chatflow 聚合。
- UAT 需要同时验证 API 响应、事件流、任务面板展示和刷新/断线后的恢复结果。

## 不在范围（Non-goals）

- 不修改节点 executor 矩阵（属于 spec 217）。
- 不引入生产 job 调度（属于 spec 218）。
- 不引入运维面板（属于 spec 220）。

## 与前序 spec 的依赖

- 前置：spec 215 ALL GREEN（frontier scheduler 已上线）。
- 文档 §15 顺序：本 spec 是 "Chatflow / SOP 兼容"，在 scheduler 上线后立即执行。

## Slice 列表

| Slice | 内容 | 主要门禁 |
|-------|------|----------|
| 216.1 | Chatflow 中断 / resume：信息收集、问题、人工输入、转人工节点在 DAG 下 waiting 状态集合正确，resume 只恢复对应节点 | RED / Unit / Integration / E2E / UAT |
| 216.2 | Chatflow 最终回复规则在多路径下生效：End 优先 / answer mapping / priority / side-effect-only / 结构化执行摘要 | RED / Contract / Integration / UAT |
| 216.3 | SOP Router 路由账本字段集收敛 + 通过聚合 child Chatflow 暴露 current_step / pending_prompt / collected / scoped_variables / checkpoint / node events / run status | RED / Unit / Integration / Contract |
| 216.4 | SOP UAT 矩阵 12 条全量通过（API 响应 / 事件流 / 任务面板 / 刷新恢复） | UAT 全套 |
| 216.5 | 客服 worker 状态消费：running / waiting / completed / failed / cancelled 全状态机覆盖 | RED / Integration / E2E |
| 216.6 | 出口回归：spec 212 + 213 + 214 + 215 入口门禁全套 | All gates |

## 实施状态

- 216.1 已完成：runtime result/status 投影新增 `waitingNodes` 与
  `waitingNodeKeys`，按每个 node 的最新 node-run 聚合 WAITING 集合，并在终态
  run 中清空旧 waiting node-run，避免 resume 后展示脏等待状态。新增 Chatflow
  fan-out side-effect + question regression，确认 resume 只恢复 waiting 节点，
  不重跑已完成 side-effect 节点。
- 216.2 已完成：多路径 Chatflow final reply selection 覆盖 End 优先、answer
  mapping、priority reply、全路径 side-effect-only summary；runtime 会把
  `sideEffectOnly` 节点输出排除在 answer mapping / priority reply 候选之外，
  防止内部通知内容变成用户可见 assistant reply。
- 216.3 已完成：RuntimeLab ledger schema 移除 `checkpoint_id` 与执行态镜像，
  RuntimeLab 事件不再写 `currentStep`，`chatflow-trace` 聚合 `currentStep /
  pendingPrompt / collected / scopedVariables / checkpoint / nodeEvents /
  runStatus` 均来自 child Chatflow run/checkpoint/event/session；历史 ledger
  payload 在 trace 中会过滤执行态镜像键。
- 216.4 已完成：新增 SOP runtime v2 12-case matrix manifest 与浏览器矩阵脚本，
  覆盖强意图启动、活动 SOP 继续、中断切换、恢复 offer、原 child run 恢复、
  非可中断拒绝切换、显式恢复、澄清不建 run、FAQ/RAG 不污染状态、Agent
  fallback 不替换状态、人工转接保持 refs、多 child run 仅聚合；每条 case
  记录 API response、event stream、task panel、refresh recovery 与截图。
- 216.5 已完成：新增 customer-assistant worker state machine integration
  matrix，覆盖 RUNNING / WAITING / COMPLETED / FAILED / CANCELLED；修复
  `CANCELLED` 被票号 PII sanitizer 误 redaction 的状态投影问题，并让 worker
  CANCELLED result 产出 `task_cancelled` 事件。Browser UAT 通过真实任务控制 API
  触发取消态，并加载失败态任务面板截图。
- 216.6 已完成：重跑 spec 212-215 出口回归门禁，backend unit / integration /
  contract、frontend unit / rem 全绿；Browser UAT 15 条脚本全绿，包含 14 条
  Chatflow/Workflow 脚本与 RuntimeLab scale `15 scenarios, 5 switches`。
  baseline evidence 已追记 spec 216 exit。

## 验收门禁映射（Acceptance Gate Map）

| 文档验收标准 | 对应 slice | 检测命令 |
|------------|-----------|---------|
| 默认 Chatflow 步骤推进 / 多路径仅明确触发 | 216.1, 216.2 | spec 212 Chatflow UAT 全套 |
| 中断 + resume 不重跑已完成 side-effect 节点 | 216.1 | `rtk node frontend/e2e/chatflow-resume-reliability.mjs`、`tests/integration/chatflow/test_resume_no_replay_side_effect.py` |
| waiting 节点集合可表达 | 216.1 | `tests/contract/runtime/test_waiting_node_set.py` |
| Chatflow 最终回复规则 | 216.2 | spec 214.4 套件 + `tests/integration/chatflow/test_final_reply_rules.py` |
| SOP Router 账本字段集（白名单） | 216.3 | `tests/unit/runtime_lab/test_sop_router_ledger_schema.py` 升级 |
| SOP Router 不持有 Chatflow 执行状态字段 | 216.3 | `tests/integration/runtime_lab/test_no_state_mirroring.py` |
| 字段从 child Chatflow 聚合 | 216.3 | `tests/contract/runtime_lab/test_aggregate_from_child_chatflow.py` |
| SOP UAT 12 条矩阵 | 216.4 | `rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` + 子矩阵脚本（含 12 case） |
| 客服 worker 状态全覆盖 | 216.5 | `rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs` |

## 文档关联

- Source: `docs/chatflow-workflow-production-upgrade.md` §8
- Gates: `docs/testing/acceptance-gates.md`
- Prior baseline evidence: `artifacts/slices/baseline-2026-06-26-runtime-prod-upgrade/baseline.md`
- Semantics doc: `docs/runtime/dag-semantics.md`
