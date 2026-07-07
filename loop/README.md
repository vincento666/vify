# Hify Loop Adapter

本目录只定义 Hify 项目如何落地 Loop Engineering。Loop Engineering 在本项目中表示：

```text
选定 spec/slice -> RED -> 实现 -> 验证 -> 评审 -> 记录 -> 下一个 slice / 停止
```

本文件不替代 `AGENTS.md`、Spec Kit 或测试门禁；它只说明当前项目的事实来源、
运行时文件和停止条件。

## 事实来源

开始任何实现前先读：

- `AGENTS.md`
- `specs/README.md`
- active spec 的 `spec.md`、`plan.md`、`tasks.md`
- `docs/testing/acceptance-gates.md`
- 本目录的 `CURRENT.md`、`STATE.md`、`VERIFIERS.md`、`LESSONS.md`，若存在

不要创建 `docs/specs/current.md`。当前 spec 指针只放在 `loop/CURRENT.md`。

## 运行时文件

```text
loop/
  README.md      # 本地 adapter
  CURRENT.md     # active spec、slice、冻结范围、停止条件
  STATE.md       # 当前状态、尝试、失败、证据、next action
  VERIFIERS.md   # 本 sprint 必跑命令
  LESSONS.md     # 单次经验、重复模式、改进候选
  PROMPTS.md     # 可选；只放项目专属短 prompt
```

`STATE.md` 只写高信号摘要和证据链接，不粘贴完整日志。

## 启动前检查

缺任一项时停在澄清阶段，不进入实现：

- active spec 已确定。
- 当前 slice 已存在于 `tasks.md`，且范围已冻结。
- 目标行为已体现在 `spec.md` / `plan.md` / `tasks.md`。
- 验收标准可客观验证，或已标明人类验收方式。
- `VERIFIERS.md` 已列出本 sprint 精确命令。
- Worktree/branch 策略已记录在 `CURRENT.md`。
- 需要的证据目录已确定：`artifacts/slices/<spec-id>/<slice-id>/`。

## Slice 规则

- 默认在同一个 active spec 内连续推进已定义 slice。
- 用户说 `single-slice`、`完成后停止`、`等我确认` 时，只做当前 slice。
- 不得自动新增 slice、重排 slice、扩大 active spec 范围。
- 行为变更必须先有 RED 证据，再写最小实现。
- 当前 slice 未全绿，不得进入下一个 slice。

## Worktree

- Branch Preflight：开始写入前运行 `git status --short`、`git branch --show-current`、
  `git worktree list`，记录 base branch、loop branch/path、merge target 和 dirty 状态。
- 并行推进不同 feature/spec/slice 时，使用独立 branch/worktree。
- 同一 slice 内 Builder 可写；Checker/Reviewer 只读检查同一 worktree。
- 使用当前 worktree 时，在 `CURRENT.md` 记录为什么足够独占。
- 无关 dirty changes、目标分支不明、需要破坏性切换或权限不足时，停止等人确认。

## Git Gates

- Slice Commit Gate：每个 slice 全绿后，在当前 loop branch 提交一次 commit。
- commit 前必须满足：verifiers 全绿、Reviewer 无 blocker、证据和文档已更新、diff 未超出冻结范围。
- commit message 必须绑定 `spec-id` 和 `slice-id`。
- 不得提交无关改动、密钥、噪音生成物、弱化的测试或门禁。
- Merge Gate：active spec 完成或用户要求合并时才合并。
- merge/PR 前重新跑必要 verifiers，确认所有 slice 已提交、工作区干净、目标分支明确。
- 冲突、验证失败、未提交改动、目标分支不明、scope drift 或需要 push/release 时，停止等人确认。

## Verifiers

`VERIFIERS.md` 只放当前 sprint 必要命令，优先使用仓库既有 pytest、ruff、mypy、
frontend test/build 命令。涉及前端视觉尺寸时加入 rem gate；涉及用户可见流程时
加入 Browser UAT 和截图证据。

## 证据

使用既有目录：`artifacts/slices/<spec-id>/<slice-id>/`，包含 RED、unit、
integration、e2e、uat 和截图证据。

完成后更新 active spec 的 `tasks.md` 证据链接。没有 checker 原始结果或 artifact，
不得声称成功。

## 停止条件

出现以下任一项，停止实现并写入 `STATE.md`：

- spec/task 缺失、错误，或需要新增/重排 slice。
- 验收标准不客观，且没有人类验收路径。
- 需要新增依赖、架构改动、数据模型/API 契约改动、权限、生产、发布、真实数据、外部服务或不可逆操作。
- 同一失败连续两轮出现，或失败数量连续两轮没有减少。
- 修复导致已通过检查失败。
- git 分支/worktree/merge target 不明确，或存在无关 dirty changes。
- slice 已完成但无法安全提交。
- merge/PR 发生冲突、验证失败或需要 push/release 授权。
- Browser UAT、数据库、live model、Chrome-MCP 或外部环境受阻，且无本地 fallback。
- Builder 试图弱化、删除、跳过测试、verifier、spec 或门禁。
- Checker 缺失、证据不足，或 Reviewer 发现范围扩张/门禁绕过。

停止时只允许补充只读证据、记录状态和列出选项。

## 记录要求

`STATE.md` 至少保持：

```text
Status:
Active spec:
Current slice:
Frozen scope:
Worktree:
Commit:
Attempts:
Checker evidence:
Reviewer findings:
Next action:
Waiting human:
```

`LESSONS.md` 只写可复用经验。重复出现或能防止高风险失败时，标记为
`Skill Improvement Candidate`，等待人类确认。
