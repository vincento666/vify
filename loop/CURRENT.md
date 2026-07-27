# Current Loop Scope: RuntimeLab Intent Routing Reliability Program

## Status

    mode: Closed Loop / Goal accepted
    contract: specs/228-runtime-policy-replay-and-uncertainty/tasks.md
    accepted roadmap: Specs 228 -> 229 -> 230 -> 231
    architecture decision: docs/adr/0010-runtime-route-decision-and-execution-boundary.md
    active unit: 228.5
    state: READY_FOR_228.5_CHECKER_DELIVERY_RECHECK
    branch: codex/spec-228-runtime-lab-intent-routing-reliability-560c
    worktree: /Users/vincento/.codex/worktrees/560c/hify

## Goal

让 RuntimeLab 的意图路由从“有限候选 + 单目标分类”收敛为可评测、可解释、
能处理不确定性和多意图、且不会把分类置信度误当执行权限的生产级决策边界；
同时保持 Chatflow 为 SOP 执行状态唯一真相，保持公开 API/SSE 兼容。

## Seven Improvement Slices

| Slice | Contract | Outcome |
|-------|----------|---------|
| S0 | Spec 228 | 评测通过与生产相同的共享决策实现，消除平行启发式 false green |
| S1 | Spec 228 | 服务端统一执行置信度、结果一致性与定向澄清门 |
| S2 | Spec 229 | 多源候选先融合再 Top-K，并用 Top-1/Top-2 margin 拦截歧义 |
| S3 | Spec 229 | 从 RuntimeLab ledger 与子 Chatflow 派生只读、有界、脱敏的 RouteContextSnapshot |
| S4 | Spec 229 | 建立版本化 Intent Catalog 与独立 IntentRetriever，和 FAQ/RAG 答案知识隔离 |
| S5 | Spec 230 + ADR 0010 | 在任务 mutation 与 Runtime V2 side effect 前分别执行可信授权门 |
| S6 | Spec 231 | 保留复合意图原子组件与关系，先澄清/确认，再逐个走正常执行门 |

## Accepted Contract

2026-07-26 用户接受完整落地 Specs 228-231，并授权：

- 使用独立 `codex/` 分支与 worktree；
- 按 slice 取得可观察 RED、最小 GREEN、独立 Checker/Reviewer；
- 创建选择性 slice commit 并 push 当前分支；
- 合同提交并推送后，另开 Codex 任务进入 Loop 持续推进到 Program Goal Gate。

固定的架构选择：

- Chatflow 继续拥有 current step、checkpoint、variables、node events 与 run
  state；RuntimeLab 不镜像子执行状态。
- 路由评测与 RuntimeLab 共享一个真实决策实现；fixture 或平行字符串匹配不能充当
  production truth。
- 默认使用 code-first Intent Catalog 和本地确定性 IntentRetriever；本合同不依赖
  live embedding 或 LLM provider。
- 分类器只提出有限候选；Spec 230 execution gate 才能授权 mutation/effect。
- Spec 230 只覆盖 conversation/session execution surfaces；现有
  route-model connectivity 与 fallback-agent administration 的访问控制是明确
  follow-up，本 Program 不得声称 RuntimeLab 全端点已授权。
- 复合意图只形成 bounded route plan；不引入通用 DAG、并行 active task 或第二
  workflow runtime。

## Frozen Sequence

1. Spec 228 Goal Gate 未 `ALL GREEN`，不得激活 Spec 229。
2. Spec 229 Goal Gate 未 `ALL GREEN`，不得激活 Spec 230。
3. Spec 230 security/fresh-review Gate 未通过，不得激活 Spec 231。
4. Spec 231 Program Goal Gate 通过后停在 delivery gate；不得自行 merge、建 PR
   或 deploy。

一次只激活一个最小垂直行为。每个 implementation slice 必须：

`tdd preflight -> observable RED -> minimal GREEN -> refactor -> applicable
gates -> diff/secret review -> independent Checker -> Reviewer -> slice commit
-> push -> Loop snapshot`

## Branch Preflight

- Branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- Base: `815cb1c90031a9dfb1e11e325a1ecf6ed48c0441`
- Merge target: `not-authorized`
- 原 checkout `/Users/vincento/work/develop/hify` 有大量用户/先前 Spec 227
  未提交变更；本 Loop 不读取为本分支事实、不暂存、不覆盖、不清理。
- 本计划从 228 编号，明确为并行的 Spec 227 保留其编号，避免未来交付碰撞。
- 当前 worktree 从上述 immutable base 创建；合同范围仅为 Specs 228-231、
  ADR 0010、Loop pointers、后续实现/测试/证据。

## Goal Controls

- success predicate: 四个 Spec 各自 Success Predicate 及最终 Program Goal Gate；
- independent evidence: 每 slice Checker 与 Reviewer；Spec 230
  `fresh-required` security review；
- max attempts: 3 次定向修复 / slice；同类 security finding 2 次；
- TTL: 从首个 implementation write 起 21 个自然日；
- provider budget: `0` live/paid calls；
- exhaustion: `WAITING_HUMAN`；
- review context: standard；Spec 230 fresh-required；
- Git delivery: commit/push authorized；PR/merge/deploy unauthorized。

## Stop Conditions

- 产品语义、权限模型、公开破坏性契约或数据库所有权无法由现有合同推导；
- 需要 live/paid provider、生产身份系统、生产数据写入或新基础设施；
- 需要平台级强制 Runtime V2 授权迁移、通用 planner/DAG 或并行 active tasks；
- MySQL/Browser 等必需能力经有界恢复仍不可用；
- 三轮定向修复耗尽，或 Spec 230 存在未关闭 Critical/High；
- 超过当前 branch 的 commit/push 权限。

## Next Action

228.5 自动门与 Reviewer 已通过；Checker round 1 仅要求把 Goal Gate 证据和
既有 228.3 尾部空行清理提交到干净 worktree，再作最终 `ALL GREEN` recheck。
完成该 recheck、push 和 Loop snapshot 前，Goal Gate 未绿，不得激活 Spec 229。
