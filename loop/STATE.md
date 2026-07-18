# Loop State

## Spec 226 Closed Loop

- date: 2026-07-18
- mode: Closed Loop
- state: `READY`
- contract: `specs/226-ai-assistant-runtime-convergence-shell/tasks.md`
- ADR: `docs/adr/0005-ai-assistant-runtime-job-substrate.md`
- active unit: `226.3`
- implementation: 226.1/226.2 shared Agent Harness and both product Adapters green
- external provider calls: 0
- production/deploy/git delivery actions: none

## Confirmed Repository Facts

- `runtime_jobs` 已有 owner、claim/lease/heartbeat、retry/DLQ 和 standalone
  worker，但实现归属 `workflow`。
- AI Assistant 仍有 router-level executor/in-flight 状态；前端仍调用
  `/worker/process`。
- RequestContext 默认从未验证 header 读取，approval/control actor 来自 body。
- AI Assistant SSE 生成器复用 request service/session。
- 当前“已处理”分组 identity 随 sequence range 变化，粒度不是稳定 phase/step。
- Customer Assistant 有真实 subagent lifecycle；AI Assistant 默认 bridge 只返回
  link/reserved refs，不能证明运行中。

## Architecture Decision

- Accepted：每个 Module 保持清晰 Interface/Implementation，复用不变量抽为公共
  deep Module，业务差异留在 Adapter。
- Accepted：Agent Harness 是 AI Assistant / Customer Assistant 共用底层；拥有
  bounded ReAct、plan、tool governance、context/memory、permission/approval、
  checkpoint/cancel/event 的通用执行不变量。
- AI Assistant 与 Customer Assistant 都通过 Agent Harness Interface；不建立
  Customer Assistant -> AI Assistant 产品依赖。
- 复用 runtime_jobs 机制，但提升为 domain-neutral substrate。
- AI Assistant/Workflow/Chatflow 各自注册 handler。
- 公共 Agent Execution Module 只拥有 parent-child identity/lifecycle/capabilities；
  Agent Harness 通过 child-provider Adapter 使用。
- Agent Harness 的外部 Seam 保持小，产品 storage、business task、UI 与工具
  Implementation 不进入公共 Module，避免 Agent God Module。
- 禁止 catch-all `common/shared/utils`；一个 Adapter 不创建假 Seam。
- raw events 保持审计真相；RunActivity 是 pure projection，不建第二活动表。

## Visual Reference

- 已截取当前 Codex 正在运行会话用于结构参考。
- 采纳：inline streaming、running row、completed one-line collapse、step count。
- 不采纳：系统暗黑色、灰阶/品牌色、侧栏/环境面板和像素值。
- Hify 保持现有亮色 tokens、`rem`、a11y 与 reduced-motion。

## Goal Controls

- max attempts: 3 / slice；2 / exit regression
- TTL: human acceptance 后 14 日
- budget: 无机器 token budget；0 live provider calls
- exhaustion: `WAITING_HUMAN`
- review context: `standard`

## Worktree Safety

- Branch: `codex/spec-226-agent-harness-convergence`
- Base: `e0c5eb356dcdad2945ebc1304c7c34b830ddcc0c`
- Merge target: `not-authorized`
- Contract 前已有多组变更；均保留。
- 226.1 已 selective commit；226.2 进入 selective Slice Commit Gate。
- 本合同没有 push、merge、deploy、provider call 或 migration apply。
- Contract docs 不构成 Unit/Integration/E2E/Browser UAT PASS。

## Next Action

226.2 Builder GREEN，Checker `ALL GREEN`，Reviewer `PASS`。完成 selective
Slice Commit Gate 后，下一步执行 226.3 TDD preflight，并取得 runtime job
owner collision、模块归属和 standalone handler RED。
