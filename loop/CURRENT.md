# Current Loop Scope: Spec 226 AI Assistant Runtime Convergence

## Status

    mode: Closed Loop
    contract: specs/226-ai-assistant-runtime-convergence-shell/tasks.md
    decision: docs/adr/0005-ai-assistant-runtime-job-substrate.md
    active unit: 226.2
    state: READY
    branch: codex/spec-226-agent-harness-convergence

## Goal

把 AI Assistant 已验证的 Harness 执行不变量抽为 Agent Harness 公共深层 Module，
让 AI Assistant 与 Customer Assistant 通过 Adapter 共用；再把单进程 worker 收敛到
durable `runtime_jobs` 的领域中立执行底座，补齐可信身份与 HA，交付 Hify 亮色活动流
和真实子智能体存在态，最后按 caller/contract 证据清理重复与历史路径。

## Frozen Scope

- Foundation：Agent Harness Interface、Customer Assistant Adapter、AI Assistant
  Adapter 与产品间反向依赖修复。
- P0：领域中立 runtime job core、trusted principal/scope、server-derived actor、
  durable AI Assistant standalone worker、takeover/cancel/SSE short-session。
- P2：stable RunActivity projection、Hify 亮色运行/完成折叠、计划步数和一层真实
  child lifecycle/presence。
- Cleanup：只删除已被 green replacement 覆盖且无 accepted contract/production
  caller/migration obligation 的路径。

不在范围：新 broker、Kubernetes HA、OS/container sandbox、递归 multi-agent、
真实 provider 消费、生产 migration/deploy、push、PR、merge。

## Accepted Contract

2026-07-18 人类已确认：

1. Agent Harness 是 AI Assistant 与 Customer Assistant 共用的公共深层 Module；
   两个产品都是 Adapter，Customer Assistant 不 import AI Assistant 产品模块。
2. Agent Execution 只拥有 child identity/lifecycle/refs；Execution Substrate
   只拥有 durable job/lease/retry/DLQ。
3. 接受 owner-aware runtime job unique key 的 Alembic migration。
4. 接受 `/worker/process` 兼容迁移及条件删除。
5. 接受 production principal 不再信任任意 header/body actor。
6. 接受默认 registry 的 demo/stub 隔离规则。

## Branch Preflight

- Branch: `codex/spec-226-agent-harness-convergence`。
- Base: `e0c5eb356dcdad2945ebc1304c7c34b830ddcc0c`。
- Merge target: `not-authorized`；本 Loop 不执行 merge。
- Worktree 当前已有多组 tracked/untracked 变更，属于用户/先前 Loop 工作。
- 本合同只修改 Spec 226/ADR、Agent Harness/Adapter slice、对应测试与证据，
  并更新当前 Loop 指针/verifier。
- 不暂存、提交、覆盖或清理无关现有改动。

## Stop Conditions

- 命中未知外部 consumer、生产数据/部署、真实成本、新 infra 或范围扩大时停止。
- 每 slice 最多 3 轮定向修复；Goal 启动后 TTL 14 日。
- Agent Harness 需要吸收产品 storage/schema/business task/UI 时停止并收窄。
- 226.1/226.2 未 ALL GREEN 不进入 runtime/HA；P0 未 ALL GREEN 不进入 P2；
  fake child/fixture 不能作为运行中子智能体证据。

## Next Action

执行 `tdd` preflight，取得 AI Assistant live ReAct 未通过公共 Agent Harness
Interface、且 tools 反向 import Customer Assistant helper 的可观察 RED。

## Previous Closed State

此前 Runtime V2/Workflow 集成已在 `e0c5eb3` 本地完成；两份历史 Spec-225、
Spec 188/190 和 Spec 224 的行为/证据继续由各自 spec、artifact 与 git 历史承载，
不再复制到 CURRENT。
