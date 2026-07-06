# Loop Lessons

本文件记录 Hify loop 的高信号经验、重复失败模式，以及可能需要升级到 Codex
skill 的改进候选。

默认规则：

- 每次 sprint 或重要 loop 结束后，先把经验记录在本文件。
- 单次经验只沉淀，不直接修改 skill、`AGENTS.md`、verifier 或 Spec Kit 规则。
- 同类问题重复出现至少两次，才生成 `Skill Improvement Candidate`。
- 修改全局 skill、项目级 skill、`AGENTS.md`、`loop/README.md`、verifier 模板或
  Spec Kit 规则前，必须 human gate。
- 不记录完整聊天、完整日志、密钥、隐私数据或低价值噪音。

## Lesson Inbox

| Date | Spec / Slice | Trigger | Lesson | Evidence | Reuse Scope | Count |
|---|---|---|---|---|---|---|
| 2026-07-01 | `222.2 StreamingRuntime` | 完成 sprint 后整理状态 | 不要把 `loop/STATE.md` 或 `loop/VERIFIERS.md` 当作 spec source；需求事实仍来自 `specs/<spec-id>/spec.md`、`plan.md`、`tasks.md`。 | `loop/STATE.md` final lessons | Hify loop protocol | 1 |
| 2026-07-01 | `222.2 StreamingRuntime` | 冻结 scope 时防止范围扩张 | `222.2` 必须排除 durable queue、ToolRunner、FileWorkspace、memory、skill、permission、sandbox、resource-lock 和 real adapter work。 | `loop/STATE.md` final lessons | Spec 222 sprint scoping | 1 |
| 2026-07-01 | Loop protocol design | 用户要求经验先沉淀再升级 | 每轮使用后的 lesson 先进入 `loop/LESSONS.md`；只有重复出现或具备明确高风险预防价值时，才生成 `Skill Improvement Candidate`。 | 本文件与 `loop/README.md` | Hify loop protocol | 1 |
| 2026-07-01 | Loop protocol design | 用户确认是否需要逐 slice 人工指示 | 在一个已确认 active spec 内，默认允许连续推进多个已定义 slice；只有触发 human gate、stop rule、用户要求 single-slice 或没有下一个已定义 slice 时才停止。 | `loop/README.md` 与 `AGENTS.md` | Hify loop protocol | 1 |
| 2026-07-01 | Loop protocol design | 用户询问 goal 尺度是否等于 slice | 外层 `/goal` 默认是一次人类授权的运行窗口，可包含多个 slice sprint；自动推进下一个 slice 时不重新发起外层 `/goal`，只更新 loop 运行时文件。 | `loop/README.md` | Hify loop protocol | 1 |
| 2026-07-01 | Loop protocol design | 用户追问 goal 执行中遇到停止条件是否能停住 | Human gate / stop rule 触发后必须进入 `waiting-human` 执行状态：停止 Builder、不进入下一 slice、只补只读证据、更新状态和提问；系统级 goal blocked 状态需遵守 goal 工具自身规则。 | `loop/README.md`、`AGENTS.md` | Hify loop protocol | 1 |
| 2026-07-02 | `222.3 ToolRuntime And Adapter Seam` | Reviewer 多轮发现同一 failure-semantics 家族问题 | 工具失败语义必须一次性覆盖 direct、serial scheduled、read-parallel scheduled、approval-resume 四条执行路径；只修当前被指出的路径，会让同类 bug 在 sibling path 反复出现。 | `loop/STATE.md` waiting-human、`red-reviewer-round2/3/4/5/6.txt` | AI Assistant ToolRuntime slices | 2 |
| 2026-07-02 | `222.3 ToolRuntime And Adapter Seam` | Human option 2 后补 read-parallel RED | 并发工具批次一旦已经启动多个 sibling，失败 finalization 必须先持久化每个已启动 sibling 的 terminal toolCall/event，再 `run.failed`；否则审计会漏掉真实执行过的工具。 | `red-reviewer-round6.txt`、`contract.txt` | AI Assistant scheduler/tool runtime | 1 |
| 2026-07-02 | `222.5 SessionRuntime` | Reviewer 发现取消 run 后 stale approval 仍可执行工具 | Session control 测试不能只断言 run status/checkpoint；必须覆盖被控制对象关联的 pending approval/proposed action 是否失效，以及 stale decision 是否被拒绝。 | `red-reviewer-round1.txt`、`contract.txt` | AI Assistant approval/session runtime | 1 |
| 2026-07-03 | `222.6 MemoryContext And ContextBudget` | Checker/Reviewer 子代理因账号用量限制失败 | 独立 Checker/Reviewer 是 slice 完成门禁；子代理不可用时不能由 Orchestrator 自己盖章，也不能进入下一 slice，应进入 `waiting-human` 并让人类选择等待 quota、授权本地 fallback，或暂停。 | `loop/STATE.md` waiting-human；subagent error notifications | Hify loop protocol | 2 |
| 2026-07-03 | `222.7-preflight PermissionPolicy / SandboxRuntime / ResourceLock` | Reviewer 发现 Open Loop contract 把 resource-lock `fencing_token` 与 CURRENT 的 worker fencing non-goal 撞词，且 lock contention / audit acceptance 不够 0/1 | 安全/权限类 preflight 也必须接受 Checker/Reviewer；contract 要把相似术语限定到具体 runtime 语义，并把 contention、shell allowlist、audit event fields 写成唯一可验证行为。 | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/reviewer-round1.md`; `reviewer-round2.md` | Safety/runtime preflight contracts | 1 |
| 2026-07-03 | `222.7 PermissionPolicy / SandboxRuntime / ResourceLock` | Reviewer round1 found real bypasses after happy-path safety events were green | 安全类 slice 的 RED 不能只证明事件存在；必须包括 threat-model cases: equivalent path bypass, shell preload/eval bypass, env/secret leakage, budget enforcement, and concurrent lock acquisition. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/red-reviewer-round1.txt`; `reviewer-round3.md` | Safety/runtime implementation slices | 1 |
| 2026-07-03 | `222.8 SkillRuntime` | Builder initially ran API contract/e2e pytest processes in parallel and saw a false failure in `test_ai_assistant_skill_runtime_api.py` | FastAPI `app.dependency_overrides` are process-global inside each pytest process; AI Assistant API suites that override `get_ai_assistant_service` should be run serially for reliable evidence. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/contract.txt`; manual debug reproduction before serial rerun | AI Assistant API test execution | 1 |
| 2026-07-04 | `222.9 TraceAuditEvalBudget` | Reviewer round1 found the eval gate could false-pass and budget degradation was only tested as a pure function | Eval/budget slices must include negative eval tests and at least one real runtime-path contract/E2E that proves thresholds and fallback policy are persisted into the run and visible in exported audit. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-round1.md` | AI Assistant eval/budget slices | 1 |
| 2026-07-04 | `222.10 Aggregate Production Evaluation` | Reviewer round1 found aggregate eval could pass on synthetic evidence and Checker missed a missing required report artifact | Aggregate/eval gates must be grounded in real artifacts or real runtime exports, and Checker must verify every artifact required by `loop/VERIFIERS.md` before PASS. Synthetic fixtures can unit-test the evaluator but cannot be the only production-evaluation proof. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/reviewer-round1.md` | AI Assistant eval/aggregate gates | 2 |
| 2026-07-06 | `222.12 Real-Time Streaming And Durable Worker Correction` | Checker/Reviewer round1 failed after local self-gates and Browser UAT had mostly passed | Independent gate FAIL must stop the loop even when local rechecks are green. Local rechecks may diagnose stale checker state, but they cannot erase missing required RED evidence or unresolved Reviewer HIGH findings. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round1.md`; `reviewer-round1.md` | Hify loop protocol | 1 |
| 2026-07-06 | `222.12 Real-Time Streaming And Durable Worker Correction` | Reviewer round2 found local green tests encoded insufficient runtime invariants | Tests for durable worker and cancellation fixes must prove structural invariants, not just one timing path: queued execution config must be frozen or atomically merged before claim, terminal completion must be CAS-guarded, and synthetic stream metadata must be consistent across related event types. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round2.md` | AI Assistant runtime correction slices | 1 |
| 2026-07-06 | `222.12 Real-Time Streaming And Durable Worker Correction` | Reviewer round3 reproduced a cancellation event leak after repository status guard passed | Cancellation-safe terminal completion must guard both state writes and terminal events. A status CAS that preserves `CANCELLED` is not enough if late paths can still emit `run.completed`; approval-resume paths need the same terminal-finalization matrix as direct and scheduled tool paths. | `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round3.md` | AI Assistant SessionRuntime terminal finalization | 1 |

## Repeated Patterns

| Pattern | Seen | Specs / Contexts | Risk | Recommended Change | Status |
|---|---:|---|---|---|---|
| Tool failure semantics reviewed path-by-path instead of as a matrix | 2 | `222.3 ToolRuntime` | Repeated reviewer blockers, possible audit/event inconsistency | Add failure-semantics matrix tests for direct, serial scheduled, read-parallel scheduled, approval-resume before closing ToolRuntime-like slices | candidate |
| Subagent quota blocks independent gate execution | 2 | Spec `213` project memory and `222.6` loop | Risk of either stalling without a clear decision or bypassing Checker/Reviewer separation | Treat unavailable subagent gates as `waiting-human`; preflight quota before long Closed Loop runs or obtain explicit fallback policy | candidate |
| Eval/report gates can false-pass on synthetic evidence | 2 | `222.9 TraceAuditEvalBudget`, `222.10 Aggregate Production Evaluation` | A slice can appear green without proving the real runtime/export/artifact path, leaving production-readiness claims ungrounded | Require aggregate/eval report tests to include one real artifact/export assembly path plus negative missing-field/missing-artifact checks before Checker PASS | candidate |
| Local green rechecks after independent FAIL can hide evidence gaps | 2 | `222.12` | Risk of self-certifying a slice despite missing required RED evidence or Reviewer HIGH findings | Treat local rechecks as diagnostic only; require new Checker/Reviewer round after targeted fixes | candidate |

## Skill Improvement Candidates

| Candidate | Target Skill | Why | Required Human Decision | Status | Updated |
|---|---|---|---|---|---|
| Require failure-semantics matrix before closing ToolRuntime-like slices | Hify loop protocol / future skill improvement | Same bug family recurred across direct, scheduled, approval-resume, and read-parallel paths; a matrix gate would prevent path-by-path reviewer churn. | Whether to promote this into `loop/README.md` or a reusable skill rule after Spec 222 | proposed | 2026-07-02 |
| Add subagent-gate availability preflight / fallback policy | Hify loop protocol / universal-work-loop skill | Subagent quota has now blocked Hify work in spec 213 and spec 222; a preflight plus explicit human-approved fallback would prevent late gate stalls or accidental self-review bypass. | Whether local fallback Checker/Reviewer is allowed when subagents are quota-blocked, and what evidence must distinguish it from independent review | proposed | 2026-07-03 |
| Require real-artifact grounding for eval/report gates | Hify loop protocol / universal-work-loop skill | The same false-pass pattern appeared in both trace/audit eval and aggregate production eval; a rule would prevent synthetic-only production readiness claims. | Whether to promote this into the project loop protocol or universal work-loop skill after Spec 222 closes | proposed | 2026-07-04 |

## Promotion Rules

将 lesson 升级为候选前，检查：

1. 是否至少重复出现两次，或能预防高风险流程问题？
2. 是否能写成稳定、可执行、可验证的行为规则？
3. 是否不会让 skill 过度拟合某个 slice 或一次失败？
4. 是否已有 spec、artifact、checker、reviewer 或运行状态证据？
5. 是否需要人类确认目标 skill 和影响范围？

## Recently Applied

| Date | Candidate | Changed File / Skill | Verification | Notes |
|---|---|---|---|---|
|  |  |  |  |  |
