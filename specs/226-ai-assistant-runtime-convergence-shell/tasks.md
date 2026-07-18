# Tasks — Spec 226

Status: `226.8 complete / 226.9 ready`

Evidence root:
`artifacts/slices/226-ai-assistant-runtime-convergence-shell/<slice>/`

## 226.0 Contract Gate

- [x] 读取 `AGENTS.md`、Loop、constitution、current state 与 acceptance gates。
- [x] 核查 `runtime_jobs` schema/repository/worker/standalone CLI 的真实边界。
- [x] 核查 AI Assistant in-process worker、SSE、权限 actor 与前端 worker 调用。
- [x] 截取并视觉核对当前 Codex 运行会话；只提取结构，不复制暗色视觉。
- [x] 写 Spec、Plan、Goal Gate、ADR 与 verifier。
- [x] Human：每个 Module 保持边界，复用不变量抽为公共 Module。
- [x] Human：确认 Agent Harness 是 AI Assistant / Customer Assistant 共用的底层
  深层 Module，两者通过 Adapter 使用，不形成产品间依赖。
- [x] Human：接受 ADR 0005 修订后的 Module 地图与 P0/P2/cleanup 冻结范围。
- [x] Human：授权按规划进入 Loop 推进本地重构；生产 migration/deploy、真实
  provider、push/merge 仍不授权。

Evidence for this contract round is the repository diff and final Contract Gate report；
未创建代码 PASS、Browser UAT PASS 或生产能力声明。

## 226.1 Foundation — Agent Harness ReAct Tracer And Customer Adapter

- [x] TDD preflight：`loop/hooks/skill-preflight.sh --required tdd`。
- [x] RED：Customer Assistant production ReAct worker 未通过公共
  `agent_harness` Interface。
- [x] RED：dependency contract 证明公共 Module 不存在或产品 Module 拥有第二套
  iteration/tool-policy/observation loop。
- [x] 建立 `app/modules/agent_harness` 的最小深层 Interface 与标准
  iteration/decision/observation/terminal semantics。
- [x] Customer Assistant Adapter 映射 `TaskItem`、worker profile、tool policy、
  proposed action 与 `WorkerResult`，保持外部行为和现有 event schema。
- [x] Interface-level contract：read-only complete、deny、approval wait、
  max-iteration。
- [x] dependency test：Agent Harness 不 import 产品/Web/infra Adapter；
  Customer Assistant 不 import AI Assistant。
- [x] Unit / Contract / Integration / SSE E2E / Docs evidence；Browser UAT、
  migration、live provider 按 `builder-handoff.md` 记为 N/A。
- [x] Checker `ALL GREEN` / Reviewer `PASS`。
- [x] Selective slice commit。

## 226.2 Foundation — AI Assistant Adapter And Dependency Repair

- [x] TDD preflight。
- [x] RED：AI Assistant live ReAct 未通过 226.1 的公共 Harness Interface。
- [x] RED：AI Assistant tools 反向 import Customer Assistant harness helper。
- [x] AI Assistant Adapter 接入现有 planner、ToolRunner、plan、context、memory、
  permission/approval、checkpoint/event stores。
- [x] 现有 ToolRunner ledger、streaming、plan 与 memory 行为保持。
- [x] shared child refs 移入 Agent Execution，移除 AI Assistant -> Customer
  Assistant 反向依赖。
- [x] 两个生产 Adapter 的 Interface-level contract 与 dependency test。
- [x] Unit / Contract / Integration / E2E / Docs evidence。
- [x] Checker / Reviewer / selective slice commit。

## 226.3 P0 — Domain-neutral Runtime Job Core

- [x] TDD preflight：`loop/hooks/skill-preflight.sh --required tdd`。
- [x] RED：不同 owner 相同 run id/job type 当前冲突。
- [x] RED：runtime job core 当前位于/import `workflow`。
- [x] RED：standalone registry 缺 `AI_ASSISTANT` handler。
- [x] Alembic migration：unique key 至少含 `owner_type`，upgrade/downgrade 和单一 head。
- [x] 提升 repository、worker state machine、registry、composition 到 runtime module。
- [x] Workflow/Chatflow adapters 注册 handler，公开行为不变。
- [x] 更新 standalone CLI owner/filter 与 operations 文档。
- [x] Unit / Contract / Integration / E2E / Docs evidence。
- [x] Checker / Reviewer / selective slice commit。

## 226.4 P0 — Trusted Principal, Scope, Permission And Audit

- [x] TDD preflight。
- [x] RED：production 任意 header 伪造 actor/tenant/workspace 被接受。
- [x] RED：body `actorId` 成为 approval/control audit actor。
- [x] RED：production `always_approve` 绕过 managed deny/sandbox。
- [x] RED：worker job payload 包含 raw credential/secret 或错误 scope。
- [x] 实现 production/local-dev/test principal resolvers。
- [x] control/approval 使用 server principal，兼容字段按合同 deprecate。
- [x] scope authorization 覆盖 run/job/event/approval/operation/memory/child。
- [x] policy fail-closed、secret ref、完整 audit。
- [x] Unit / Contract / Integration / Security evidence。
- [x] Checker / Reviewer / slice commit。

## 226.5 P0 — Durable AI Assistant Standalone Worker And HA

- [x] TDD preflight。
- [x] RED：关闭/终止 API 进程后 queued run 无法完成。
- [x] RED：双 worker / expired lease / late writer 场景。
- [x] RED：SSE 长连接占用 DB session/pool。
- [x] RED：cancel/pause/lease loss 后继续写 event/effect。
- [x] `messages/async` durable enqueue AI Assistant runtime job。
- [x] standalone handler + heartbeat/takeover + bounded backpressure。
- [x] SSE 短 session/cursor replay；外部 I/O async 或有界 compatibility adapter。
- [x] 删除 AI router autonomous executor/lock/in-flight。
- [x] 前端停止调用 `/worker/process`。
- [x] `/worker/process` 转兼容 shim 并输出 deprecation metadata。
- [x] Unit / Contract / Integration / fault E2E / Docs evidence。
- [x] Checker / Reviewer / slice commit。

## 226.6 P2 Foundation — Stable Activity And Real Child Lifecycle

- [x] TDD preflight。
- [x] RED：sequence-range 变化导致 activity ID/override 丢失。
- [x] RED：duplicate/reordered event 导致重复或回退状态。
- [x] RED：link-only bridge 被错误投影为 running subagent。
- [x] 定义公共 Agent Execution Interface 与 dependency contract。
- [x] AI Assistant / Customer Assistant 两个 Adapter 通过同一 Interface。
- [x] 为 phase/step/tool/skill/approval/subagent 写稳定 correlation ID。
- [x] 实现纯 `RunActivity` projection 与 raw event detail refs。
- [x] 实现一层真实 `SubagentExecutionRef` adapter/lifecycle。
- [x] child lifecycle 有 scope、audit、status/result refs。
- [x] Unit / Contract / Integration evidence；UI N/A（foundation only）。
- [x] Checker / Reviewer / slice commit。

## 226.7 P2 — Hify Light Activity Shell

- [x] TDD preflight。
- [x] RED：running 默认展开，completed 自动折叠。
- [x] RED：manual override 在 event upsert/SSE reconnect 后保持。
- [x] RED：failed/waiting approval 不自动折叠。
- [x] RED：真实 running child 存在态、active count、完成折叠。
- [x] RED：model delta 与活动流并行即时出现。
- [x] RED：Hify tokens/rem/reduced-motion/a11y。
- [x] 拆出 activity feed/row/subagent/progress/stream composable。
- [x] 保留 raw audit detail 与就地 approval actions。
- [x] Frontend unit / build / rem / E2E。
- [x] Browser UAT：Hify 亮色主题截图，包含 running、completed、approval/error、
  running subagent 五个状态。
- [x] Checker / Reviewer / slice commit。

## 226.8 Cleanup — Duplicate Harness, Registry And Legacy Paths

- [x] TDD/characterization preflight。
- [x] 生成 production caller、accepted-contract、route compatibility inventory。
- [x] 删除或收窄 `ControlledReActCore`、`RestrictedReactWorker`、
  `worker_registry`、`tool_policy` 中已由 Agent Harness 覆盖的第二套执行逻辑；
  Customer Assistant business Adapter 保持 locality。
- [x] demo/eval：`echo_context`、blocked update、MockAviation。
- [x] capability unavailable：stub knowledge/skill script 隔离；shell 绑定受控
  subprocess 实现。
- [x] subagent bridge：仅在 composition 注入真实 lifecycle provider 时注册。
- [x] Add Context/planning option：删除无效 Add Context；保留有真实策略差异的
  planning option。
- [x] 删除 unstable processed-group projection 与已替代 facade。
- [x] `/worker/process` 未达到外部消费者删除门；保留至 2026-08-01 的
  enqueue/inspect shim，request 内不执行。
- [x] dependency test：runtime core 无业务 import，router/shell 不重新聚合职责。
- [x] Full affected regression / Docs evidence。
- [x] Checker / Reviewer / slice commit。

## 226.9 Goal Exit

- [ ] Worker crash/takeover/lease fencing/late-write fault matrix。
- [ ] Principal spoof/cross-scope/approval replay/security regression。
- [ ] Agent Harness Interface/dependency contract；AI Assistant 与 Customer
  Assistant production Adapter 证明。
- [ ] AI Assistant unit/contract/integration/e2e/eval。
- [ ] Customer Assistant affected unit/contract/integration/e2e。
- [ ] Runtime V2 218/219 regression。
- [ ] Frontend unit/build/rem。
- [ ] Browser UAT 可重复，截图与操作记录归档。
- [ ] Alembic single head + upgrade/downgrade evidence。
- [ ] `git diff --check` 与 secret scan。
- [ ] Checker: `ALL GREEN`。
- [ ] Reviewer: `PASS`，无 blocker。
- [ ] Goal Gate: `SATISFIED`；否则按 attempts/TTL 进入 `WAITING_HUMAN`。
- [ ] Product Re-entry Review；不自动开启下一 feature。

## Stop Rules

- schema/API/security/architecture 方向超出已接受 ADR；
- Agent Harness 需要吸收产品 repository/schema、业务 task 或 UI 语义；
- 发现未知外部 `/worker/process` 消费者；
- 需要真实 provider、生产数据、部署、push/merge 或新基础设施；
- side-effect takeover 无法由 lease fencing + Spec 224 ledger 证明安全；
- 某 slice 3 轮定向修复仍未通过；
- Goal TTL 到期。
